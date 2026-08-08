#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_crashed_checker_is_not_a_finding.sh — a checker that could not run
# must not produce a verdict about the code.
#
# WHAT THIS GUARDS (.github#245, #233)
# ------------------------------------
# Two gates turned an ENVIRONMENT failure into a statement about the source:
#
#   gate-17  passed the scope list as ONE argv string,
#            `--changed-files=<404 KB>`. A single argument is capped at
#            MAX_ARG_STRLEN — 128 KiB on Linux — regardless of ARG_MAX being
#            2 MB. The exec raised E2BIG, python3 never started, and the log
#            held the shell's "Argument list too long". `grep -c '^lib/'` then
#            counted zero findings in that error text and the gate reported
#            `FAIL — 0 pass-through method(s)`: a crashed checker wearing a
#            finding count, and a count of zero at that.
#
#            Measured on openregister: root-scoped CHANGED_FILES is 404,828
#            bytes across 7,224 files — over 3x the limit — and the pre-fix
#            baseline reports exactly that FAIL — 0 line.
#
#   gate-60   reported 43 confident FAILs ("Calendar does not exist") when
#            node_modules was absent. That was fixed by guarding the existence
#            check — which swapped it for the OPPOSITE error: the rule silently
#            stops running and the gate returns 0, so the runner prints PASS
#            over a check that never executed.
#
# Both directions are the same mistake. "I could not look" is a THIRD state:
# never PASS, never a finding count that was never measured.

set -u

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_scripts="$(cd "${_here}/.." && pwd)"
_runner="${HYDRA_GATES_RUNNER_UNDER_TEST:-${_scripts}/run-hydra-gates.sh}"

_failures=0
_ok()  { echo "  ok   — $1"; }
_bad() { echo "  FAIL — $1"; _failures=$((_failures + 1)); }

echo "test_gate_crashed_checker_is_not_a_finding.sh"

_tmp="$(mktemp -d "${TMPDIR:-/tmp}/hydra-crashed.XXXXXX")"
trap 'rm -rf "${_tmp}"' EXIT

# ---------------------------------------------------------------------------
# THE MECHANISM ITSELF — a single argv string over 128 KiB is unusable.
#
# Asserted directly, because this is the fact the gate-17 fix depends on and it
# is not obvious: ARG_MAX says 2 MB, and the limit that bites is a different,
# per-argument one.
# ---------------------------------------------------------------------------
if python3 - <<'PY'
import subprocess, sys
big = "x" * (200 * 1024)
try:
    subprocess.run(["/bin/true", "--changed-files=" + big], check=True)
except OSError:
    sys.exit(0)   # E2BIG — the limit is real
sys.exit(1)       # no error: this platform does not have the limit
PY
then
    _ok "a single 200 KiB argv string raises E2BIG (the limit gate-17 tripped over)"
    _argv_limited=1
else
    echo "  note — this platform accepts a 200 KiB single argument; the file-based"
    echo "         scope path is still asserted below, but E2BIG cannot be provoked here."
    _argv_limited=0
fi

# ---------------------------------------------------------------------------
# gate-17 — a scope list far larger than MAX_ARG_STRLEN must still be inspected,
# and must NOT come back as "FAIL — 0 pass-through method(s)".
# ---------------------------------------------------------------------------
_app="${_tmp}/app"
mkdir -p "${_app}/lib/Controller" "${_app}/src"
printf '{"name":"fx","menu":[]}\n' > "${_app}/src/manifest.json"
cat > "${_app}/lib/Controller/ThingController.php" <<'PHP'
<?php
namespace OCA\Fx\Controller;
class ThingController {
    public function index() { return 1; }
}
PHP
# TWO commits: the diff has to be root..HEAD, and a repo whose root IS its HEAD
# has an empty diff — the runner refuses that outright (base == HEAD), so no
# gate would report and this arm would pass for the wrong reason.
(
    cd "${_app}" || exit 1
    git init -q .
    git add -A
    git -c user.email=t@t -c user.name=t commit -qm init
) >/dev/null 2>&1

# Enough files that the newline-joined path list clears 128 KiB comfortably.
mkdir -p "${_app}/src/filler"
_i=0
while [ "${_i}" -lt 3000 ]; do
    printf 'export const x%s = 1\n' "${_i}" \
        > "${_app}/src/filler/a-file-with-a-deliberately-long-name-${_i}.ts"
    _i=$((_i + 1))
done
(
    cd "${_app}" || exit 1
    git add -A
    git -c user.email=t@t -c user.name=t commit -qm "bulk"
) >/dev/null 2>&1

_root=$(cd "${_app}" && git rev-list --max-parents=0 HEAD | tail -1)
_scope_bytes=$(cd "${_app}" && git diff --name-only --diff-filter=ACMR "${_root}...HEAD" | wc -c)
echo "  (scope list is ${_scope_bytes} bytes; MAX_ARG_STRLEN is 131072)"

_logs="${_tmp}/logs"
mkdir -p "${_logs}"
_out="${_tmp}/run.txt"
(
    cd "${_app}" || exit 1
    HYDRA_GATE_LOG_DIR="${_logs}" bash "${_runner}" \
        --scope-to-diff --base "${_root}" . > "${_out}" 2>&1
)

_v17=$(grep -oE '^\[gate-17\] [^:]+: [A-Z]+( \([a-z]+\))?' "${_out}" | head -1 | sed 's/^[^:]*: //')
if grep -qE '^\[gate-17\][^:]*: FAIL — 0 ' "${_out}"; then
    _bad "gate-17 reported 'FAIL — 0 pass-through method(s)' — a crash rendered as a finding count"
elif [ "${_v17}" = "PASS" ] || [ "${_v17}" = "FAIL" ]; then
    _ok "gate-17 produced a real verdict (${_v17}) over a ${_scope_bytes}-byte scope list"
elif [ "${_v17}" = "SKIPPED (wiring)" ]; then
    _ok "gate-17 reported SKIPPED (wiring) — honest, though the scope file should have avoided the crash"
else
    _bad "gate-17 verdict is '${_v17:-none emitted}' — expected a real verdict"
fi

# The mechanism: the scope must travel via a FILE, not argv.
if [ -s "${_logs}/hydra-gate-17-scope.txt" ]; then
    _ok "the scope list travelled in a file, not in argv"
else
    _bad "no scope file was written — the list is still going through argv and will E2BIG again"
fi

# ---------------------------------------------------------------------------
# gate-60 — node_modules absent. Not a pass, and not 43 findings.
# ---------------------------------------------------------------------------
_icon_app="${_tmp}/icons"
mkdir -p "${_icon_app}/src"
cat > "${_icon_app}/src/manifest.json" <<'JSON'
{"name":"fx","menu":[{"label":"Calendar","icon":"Calendar","route":"/cal"}]}
JSON
(
    cd "${_icon_app}" || exit 1
    git init -q .
    git add -A
    git -c user.email=t@t -c user.name=t commit -qm init
) >/dev/null 2>&1

_ilogs="${_tmp}/ilogs"
mkdir -p "${_ilogs}"
_iout="${_tmp}/icons.txt"
(
    cd "${_icon_app}" || exit 1
    HYDRA_GATE_LOG_DIR="${_ilogs}" bash "${_runner}" . > "${_iout}" 2>&1
)

_v60=$(grep -oE '^\[gate-60\] [^:]+: [A-Z]+( \([a-z]+\))?' "${_iout}" | head -1 | sed 's/^[^:]*: //')
case "${_v60}" in
    "SKIPPED (wiring)")
        _ok "gate-60 reports SKIPPED (wiring) when vue-material-design-icons is absent"
        ;;
    PASS)
        _bad "gate-60 reported PASS while the icon-existence rule never ran — the #233 regression, inverted"
        ;;
    FAIL)
        _bad "gate-60 reported FAIL from a missing dependency — an environment failure rendered as findings (#233)"
        ;;
    *)
        _bad "gate-60 verdict is '${_v60:-none emitted}' — expected SKIPPED (wiring)"
        ;;
esac

# It must say WHAT could not be checked, not merely that something was skipped.
if grep -qE '^\[gate-60\][^:]*: SKIPPED \(wiring\) — .*vue-material-design-icons' "${_iout}"; then
    _ok "gate-60's skip names the missing dependency and what it left unverified"
else
    _bad "gate-60's skip does not name the missing dependency"
fi

# THE CONTROL: the rules that CAN run without node_modules must still run, so
# this is not "skip the gate whenever a dependency is missing".
_bad_icon_app="${_tmp}/icons-bad"
mkdir -p "${_bad_icon_app}/src"
cat > "${_bad_icon_app}/src/manifest.json" <<'JSON'
{"name":"fx","menu":[{"label":"Dashboard","icon":"CarSportOutline","route":"/d"}]}
JSON
(
    cd "${_bad_icon_app}" || exit 1
    git init -q .
    git add -A
    git -c user.email=t@t -c user.name=t commit -qm init
) >/dev/null 2>&1
_blogs="${_tmp}/blogs"
mkdir -p "${_blogs}"
_bout="${_tmp}/icons-bad.txt"
(
    cd "${_bad_icon_app}" || exit 1
    HYDRA_GATE_LOG_DIR="${_blogs}" bash "${_runner}" . > "${_bout}" 2>&1
)
if grep -qE '^\[gate-60\][^:]*: FAIL' "${_bout}"; then
    _ok "a Tier-A concept on a non-canonical icon is STILL caught without node_modules"
else
    _v=$(grep -oE '^\[gate-60\] [^:]+: [A-Z]+( \([a-z]+\))?' "${_bout}" | head -1 | sed 's/^[^:]*: //')
    _bad "gate-60 returned '${_v}' for a real violation it can detect offline — the missing dependency is now suppressing rules that DO work"
fi

echo
if [ "${_failures}" -eq 0 ]; then
    echo "test_gate_crashed_checker_is_not_a_finding.sh: ALL PASS"
    exit 0
fi
echo "test_gate_crashed_checker_is_not_a_finding.sh: ${_failures} FAILURE(S)"
exit 1
