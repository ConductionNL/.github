#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_or_abstraction_pdok.sh — self-test for rule 1 of
# scripts/lint-or-abstraction-anti-patterns.sh (shared-pdok-via-openconnector).
#
# WHY THIS EXISTS
# ---------------
# Until 2026-08-09 the rule was `grep -rl api.pdok.nl`. Measured across all 18
# Conduction app repositories at origin/development it produced three findings,
# of which TWO were the opposite of a violation:
#
#   * procest src/services/pdokService.js is the openconnector-routed shim; its
#     only match was a docblock line saying direct calls are NOT permitted and
#     citing this very rule by name.
#   * openregister lib/Service/Geo/PdokGeocoder.php matched on a const holding
#     the base URL that it hands to OpenConnector's CallService. It owns no
#     HTTP client at all.
#
# The rule now reads code rather than prose, and distinguishes a file that
# dispatches through OpenConnector from one that carries its own transport.
#
# THE POINT OF THIS SUITE is the other direction. Narrowing a matcher is how a
# gate gets quietly neutered, so the FIRE assertions below are the ratchet: a
# real direct call must keep failing, and neither a comment naming
# "openconnector" nor an unrecognised HTTP client may buy silence. If a future
# edit widens the suppression, these go red.
#
# Run: bash scripts/lib/test_or_abstraction_pdok.sh   (exit 0 = pass)
set -uo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
GATE="${LIB_DIR}/../lint-or-abstraction-anti-patterns.sh"

if [ ! -f "${GATE}" ]; then
    echo "FAIL — gate script not found at ${GATE}; this suite cannot assert anything."
    echo "Refusing to report passes for a subject that is absent."
    exit 1
fi

FAILS=0
WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

mkdir -p "${WORK}/lib/Service" "${WORK}/src" "${WORK}/appinfo"
printf '<?xml version="1.0"?>\n<info>\n  <id>fixtureapp</id>\n</info>\n' > "${WORK}/appinfo/info.xml"

# Force BLOCK mode so the exit status carries the verdict. In WARN mode the
# script returns 0 whether or not anything matched — which is exactly how these
# findings stayed invisible — so a suite that read the byte in WARN mode would
# assert nothing.
run_gate() (
    cd "${WORK}" && HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 bash "${GATE}" >"${WORK}/.out" 2>&1
    echo $?
)

assert_rc() { # <expected-rc> <label>
    local want="$1" label="$2" got
    got="$(run_gate)"
    if [ "${got}" = "${want}" ]; then
        echo "PASS — ${label}"
    else
        echo "FAIL — ${label} (expected exit ${want}, got ${got})"
        sed 's/^/        /' "${WORK}/.out"
        FAILS=$((FAILS + 1))
    fi
}

reset_tree() { rm -f "${WORK}"/lib/Service/*.php "${WORK}"/src/*.js 2>/dev/null || true; }

# --- guard the guard --------------------------------------------------------
# An empty tree must be clean. If this fails, every "did not fire" assertion
# below would pass for the wrong reason.
reset_tree
assert_rc 0 "control: empty tree is clean (so the silence assertions mean something)"

# --- MUST FIRE: real direct calls -------------------------------------------
reset_tree
cat > "${WORK}/lib/Service/Direct.php" <<'PHPEOF'
<?php
class Direct {
    public function geocode(string $q): string {
        return file_get_contents('https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?q='.$q);
    }
}
PHPEOF
assert_rc 1 "fires: file_get_contents() straight at api.pdok.nl"

reset_tree
cat > "${WORK}/lib/Service/Fopen.php" <<'PHPEOF'
<?php
class Fopen {
    private const EP = 'https://api.pdok.nl/bzk/locatieserver/search/v3_1';
    public function go(): void {
        $ctx = stream_context_create(['http' => ['method' => 'GET']]);
        $h   = fopen(self::EP.'/free', 'rb', false, $ctx);
    }
}
PHPEOF
assert_rc 1 "fires: fopen() + stream_context_create() (the procest callDirect() shape)"

reset_tree
cat > "${WORK}/src/direct.js" <<'JSEOF'
import axios from 'axios'
export const suggest = (q) => axios.get('https://api.pdok.nl/bzk/locatieserver/search/v3_1/suggest', { params: { q } })
JSEOF
assert_rc 1 "fires: frontend axios.get() straight at api.pdok.nl"

reset_tree
cat > "${WORK}/lib/Service/Bare.php" <<'PHPEOF'
<?php
class Bare {
    public const BASE = 'https://api.pdok.nl/bzk/locatieserver/search/v3_1';
}
PHPEOF
assert_rc 1 "fires: host on a code line with no OpenConnector reference — routing not demonstrable"

# --- MUST FIRE: suppression may not be bought with a comment ----------------
reset_tree
cat > "${WORK}/lib/Service/Sneaky.php" <<'PHPEOF'
<?php
// TODO: migrate this to openconnector one day.
class Sneaky {
    public function go(): void {
        $h = fopen('https://api.pdok.nl/bzk/locatieserver/search/v3_1/free', 'rb');
    }
}
PHPEOF
assert_rc 1 "fires: a COMMENT naming openconnector does not excuse a direct fopen()"

reset_tree
cat > "${WORK}/lib/Service/Unknown.php" <<'PHPEOF'
<?php
// We will route via openconnector eventually.
class Unknown {
    public function go(): void {
        $c = new \Some\Vendor\UnrecognisedRestClient();
        $c->request('GET', 'https://api.pdok.nl/bzk/locatieserver/search/v3_1/free');
    }
}
PHPEOF
assert_rc 1 "fires: an UNRECOGNISED http client still fires — the transport list is not an allowlist"

# --- MUST NOT FIRE: prose, and genuine OpenConnector routing ----------------
reset_tree
cat > "${WORK}/src/shim.js" <<'JSEOF'
/**
 * Routes all PDOK Locatieserver access through the openconnector PDOK adapter.
 * Direct browser calls to api.pdok.nl are NOT permitted from this app — see
 * Hydra umbrella `shared-pdok-via-openconnector` (ADR-022).
 */
import axios from '@nextcloud/axios'
import { generateUrl } from '@nextcloud/router'
const BASE_URL = generateUrl('/apps/openconnector/api/pdok')
export const suggest = (q) => axios.get(`${BASE_URL}/suggest`, { params: { q } })
JSEOF
assert_rc 0 "silent: the host named only in a docblock is not a call site (procest pdokService.js)"

reset_tree
cat > "${WORK}/lib/Service/Routed.php" <<'PHPEOF'
<?php
class Routed {
    public const BASE = 'https://api.pdok.nl/bzk/locatieserver/search/v3_1';
    public function go(array $p): void {
        $cs = $this->container->get('OCA\\OpenConnector\\Service\\CallService');
        $cs->call(null, self::BASE.'/free', 'GET', ['query' => $p]);
    }
}
PHPEOF
assert_rc 0 "silent: URL handed to OpenConnector's CallService (openregister PdokGeocoder)"

# The compliant cases must be REPORTED, not silently dropped — a reader has to
# be able to tell "nothing there" from "found it and judged it compliant".
if grep -q 'dispatches through OpenConnector — compliant, not counted' "${WORK}/.out"; then
    echo "PASS — compliant routing is printed as an info line, not silently dropped"
else
    echo "FAIL — compliant routing was suppressed with no output; the reader cannot audit the decision"
    FAILS=$((FAILS + 1))
fi

# --- the CAPABILITY table's grep row must read code too (#415/#423) ---------
#
# The PDOK rule above has routed through `_code_lines` since it was written.
# `OR_CAPABILITY_RULES`' one `grep`-kind row — Postgres `search_path` tenant
# isolation — never did, so a docblock saying the class deliberately does NOT
# do the thing produced a finding IDENTICAL to a real one. Both halves are
# asserted here: the documented file goes quiet, the real statement does not.
#
# ⚠️ THE CAPABILITY ROWS HAVE THEIR OWN BAKE-IN EPOCH, so `run_gate`'s forced
# BLOCK mode does NOT reach them: in WARN mode the script exits 0 whether or
# not a capability rule matched. Written as `assert_rc 0` first, BOTH halves
# passed — including on the unfixed script, where the "silent" arm was
# measuring the epoch and not the finding. Assert the FILE LIST instead, and
# force the capability epoch too so the exit status is a second witness.
assert_out() {  # <yes|no> <regex> <label>
    local want="$1" rx="$2" label="$3"
    HYDRA_OR_CAPABILITY_GATE_BLOCK_AFTER_EPOCH=0 run_gate >/dev/null
    if grep -qE "${rx}" "${WORK}/.out"; then
        if [ "${want}" = "yes" ]; then echo "PASS — ${label}"; return; fi
    elif [ "${want}" = "no" ]; then
        echo "PASS — ${label}"; return
    fi
    echo "FAIL — ${label} (expected the output ${want} to match /${rx}/)"
    sed 's/^/        /' "${WORK}/.out"
    FAILS=$((FAILS + 1))
}

reset_tree
cat > "${WORK}/lib/Service/RowFetcher.php" <<'PHPEOF'
<?php
class RowFetcher {
    /**
     * Fetch rows for the caller's organisation.
     *
     * We deliberately do NOT set a Postgres search_path here — isolation is
     * OpenRegister's job (ADR-022), and doing it locally would be an
     * app-local re-implementation of an OR-owned capability.
     */
    public function findAll(): array {
        return $this->or->objects()->all();
    }
}
PHPEOF
assert_out no "RowFetcher\.php" "silent: a docblock explaining that search_path is NOT set is not a finding"

reset_tree
cat > "${WORK}/lib/Service/RealScope.php" <<'PHPEOF'
<?php
class RealScope {
    public function scope(string $t): void {
        $this->db->executeStatement('SET search_path TO '.$t);
    }
}
PHPEOF
assert_out yes "RealScope\.php" "fires: a real SET search_path is still OR-owned-capability duplication"

# --- openconnector itself owns the adapter and is exempt --------------------
reset_tree
printf '<?xml version="1.0"?>\n<info>\n  <id>openconnector</id>\n</info>\n' > "${WORK}/appinfo/info.xml"
cat > "${WORK}/lib/Service/Adapter.php" <<'PHPEOF'
<?php
class Adapter {
    public function go(): string {
        return file_get_contents('https://api.pdok.nl/bzk/locatieserver/search/v3_1/free');
    }
}
PHPEOF
assert_rc 0 "silent: openconnector PROVIDES the PDOK adapter — exempt by app id, not by path"

echo ""
if [ "${FAILS}" -eq 0 ]; then
    echo "test_or_abstraction_pdok: all assertions passed."
    exit 0
fi
echo "test_or_abstraction_pdok: ${FAILS} assertion(s) FAILED."
exit 1
