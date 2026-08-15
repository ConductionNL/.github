#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# Self-test for check_contract_surface_shift.py (gate-83).
#
# Discovered and run by tests/run-helper-suites.sh — no workflow edit needed.
#
# Every assertion is paired: a NEGATIVE control (a shift that IS declared must
# pass) and a POSITIVE control (an undeclared shift must produce exactly that
# finding). A checker that reports nothing on a breaking change and one that
# reports nothing on a clean diff are the same program from the outside.
#
# THE BARE-ANNOTATION CASE IS NOT DECORATION. The first draft of this gate let
# a reason-less `@contract-shift announced` pass, because the regex separator
# was `\s*`, which matches newlines — so the match ran past the line end and
# captured the docblock's closing `*/` as the "reason". Non-empty, so the
# no-reason branch never fired and the escape hatch was silently open to any
# bare tag. Only this assertion caught it. It stays.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="${HERE}/check_contract_surface_shift.py"
pass=0
fail=0

ok() { echo "  PASS  $1"; pass=$((pass + 1)); }
no() { echo "  FAIL  $1"; [ -n "${2:-}" ] && printf '        %s\n' "$2"; fail=$((fail + 1)); }

# Build a repo whose base declares `getBar()` on the MAGIC surface and whose
# HEAD carries $1 as the class body.
fixture() {
    local d="$1" head_body="$2" base_body="${3:-}"
    rm -rf "$d"; mkdir -p "$d/lib/Contract" "$d/lib/Db"
    (
        cd "$d" || exit 1
        git init -q .
        git config user.email test@example.invalid
        git config user.name 'Gate Test'
        printf '<?php\ninterface FooInterface {\n\tpublic function getBar(): ?string;\n}\n' \
            > lib/Contract/FooInterface.php
        if [ -n "${base_body}" ]; then
            printf '%b' "${base_body}" > lib/Db/Foo.php
        else
            printf '<?php\n/**\n * @method string getBar()\n */\nclass Foo implements FooInterface {\n}\n' \
                > lib/Db/Foo.php
        fi
        git add -A >/dev/null
        git commit -qm base
        printf '%b' "${head_body}" > lib/Db/Foo.php
        git add -A >/dev/null
        git commit -qm head --allow-empty
    )
}

run_rc() {
    python3 "${CHECKER}" "$1" --base HEAD~1 >/dev/null 2>&1
    echo $?
}

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

DECLARED_NO_TAG='<?php\nclass Foo implements FooInterface {\n\tpublic function getBar(): ?string { return null; }\n}\n'
DECLARED_GOOD='<?php\nclass Foo implements FooInterface {\n\t/**\n\t * @contract-shift announced — consumers named in openregister#2498.\n\t */\n\tpublic function getBar(): ?string { return null; }\n}\n'
DECLARED_BARE='<?php\nclass Foo implements FooInterface {\n\t/**\n\t * @contract-shift announced\n\t */\n\tpublic function getBar(): ?string { return null; }\n}\n'
DECLARED_BADCAT='<?php\nclass Foo implements FooInterface {\n\t/**\n\t * @contract-shift whatever — a reason.\n\t */\n\tpublic function getBar(): ?string { return null; }\n}\n'
MAGIC='<?php\n/**\n * @method string getBar()\n */\nclass Foo implements FooInterface {\n}\n'

echo "check_contract_surface_shift.py (gate-83)"

# POSITIVE: magic -> declared with no annotation is the fleet-breaking change.
fixture "${TMP}/a" "${DECLARED_NO_TAG}"
rc=$(run_rc "${TMP}/a")
[ "${rc}" = "1" ] && ok "undeclared magic->declared shift fails" \
    || no "undeclared magic->declared shift fails" "rc=${rc}, expected 1"

# NEGATIVE: the same shift, properly declared, passes.
fixture "${TMP}/b" "${DECLARED_GOOD}"
rc=$(run_rc "${TMP}/b")
[ "${rc}" = "0" ] && ok "annotated shift passes" \
    || no "annotated shift passes" "rc=${rc}, expected 0"

# POSITIVE: a bare tag with no reason is not an escape hatch.
fixture "${TMP}/c" "${DECLARED_BARE}"
rc=$(run_rc "${TMP}/c")
[ "${rc}" = "1" ] && ok "bare annotation with no reason fails" \
    || no "bare annotation with no reason fails" "rc=${rc}, expected 1 (the \\s* newline bug)"

# POSITIVE: the category vocabulary is closed.
fixture "${TMP}/d" "${DECLARED_BADCAT}"
rc=$(run_rc "${TMP}/d")
[ "${rc}" = "1" ] && ok "invalid category fails" \
    || no "invalid category fails" "rc=${rc}, expected 1"

# POSITIVE: the REVERSE shift breaks onlyMethods() doubles and must also fail.
fixture "${TMP}/e" "${MAGIC}" "${DECLARED_NO_TAG}"
rc=$(run_rc "${TMP}/e")
[ "${rc}" = "1" ] && ok "undeclared declared->magic shift fails" \
    || no "undeclared declared->magic shift fails" "rc=${rc}, expected 1"

# NEGATIVE: a diff touching no contract file is EMPTY SCOPE, never a PASS.
fixture "${TMP}/f" "${MAGIC}" "${MAGIC}"
( cd "${TMP}/f" && mkdir -p lib/Other && printf '<?php\nclass Other {}\n' > lib/Other/Other.php \
    && git add -A >/dev/null && git commit -qm unrelated ) >/dev/null 2>&1
rc=$(run_rc "${TMP}/f")
[ "${rc}" = "3" ] && ok "diff with no contract file reports empty scope, not pass" \
    || no "diff with no contract file reports empty scope, not pass" "rc=${rc}, expected 3"

# NEGATIVE: a repo publishing no contract is NOT APPLICABLE.
NOCONTRACT="${TMP}/g"
rm -rf "${NOCONTRACT}"; mkdir -p "${NOCONTRACT}/lib"
( cd "${NOCONTRACT}" && git init -q . && git config user.email t@example.invalid \
    && git config user.name 'Gate Test' && printf '<?php\nclass X {}\n' > lib/X.php \
    && git add -A >/dev/null && git commit -qm base && git commit -qm second --allow-empty ) >/dev/null 2>&1
rc=$(run_rc "${NOCONTRACT}")
[ "${rc}" = "4" ] && ok "repo with no lib/Contract is not applicable" \
    || no "repo with no lib/Contract is not applicable" "rc=${rc}, expected 4"

# POSITIVE: an unresolvable base FAILS CLOSED. A broken scope must never be
# reported as an empty one — that is how a broken gate reads as a green gate.
python3 "${CHECKER}" "${TMP}/a" --base no-such-ref-exists >/dev/null 2>&1
rc=$?
[ "${rc}" = "1" ] && ok "unresolvable base fails closed" \
    || no "unresolvable base fails closed" "rc=${rc}, expected 1"

# WIRING: the terminal summary line the runner greps for must be printed, or
# the runner cannot tell a clean run from a crashed one.
out="$(python3 "${CHECKER}" "${TMP}/a" --base HEAD~1 2>&1 || true)"
# A real if/then/else, not `A && B || C`: in that form C also runs when A is
# true and B fails, so a passing assertion could report both PASS and FAIL.
if printf '%s' "${out}" | grep -qE '^checked [0-9]+ contract '; then
    ok "prints the terminal summary the runner asserts on"
else
    no "prints the terminal summary the runner asserts on" "got: ${out}"
fi

echo "  ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
