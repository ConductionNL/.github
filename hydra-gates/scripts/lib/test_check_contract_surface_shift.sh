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
#
# Assertions go through `expect_rc`, a real if/then/else. `A && ok || no` reads
# like one and is not: the failure branch also runs when the check passes and
# the reporter fails, so a single assertion could print both PASS and FAIL
# (ShellCheck SC2015).
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="${HERE}/check_contract_surface_shift.py"
pass=0
fail=0

ok() { echo "  PASS  $1"; pass=$((pass + 1)); }
no() { echo "  FAIL  $1"; [ -n "${2:-}" ] && printf '        %s\n' "$2"; fail=$((fail + 1)); }

# expect_rc <actual> <expected> <label> [detail]
expect_rc() {
    if [ "$1" = "$2" ]; then
        ok "$3"
    else
        no "$3" "rc=$1, expected $2${4:+ — $4}"
    fi
}

# Build a repo whose base declares `getBar()` on the MAGIC surface and whose
# HEAD carries $2 as the class body. $3 overrides the base body.
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
expect_rc "$(run_rc "${TMP}/a")" 1 "undeclared magic->declared shift fails"

# NEGATIVE: the same shift, properly declared, passes.
fixture "${TMP}/b" "${DECLARED_GOOD}"
expect_rc "$(run_rc "${TMP}/b")" 0 "annotated shift passes"

# POSITIVE: a bare tag with no reason is not an escape hatch.
fixture "${TMP}/c" "${DECLARED_BARE}"
expect_rc "$(run_rc "${TMP}/c")" 1 "bare annotation with no reason fails" \
    "this is the \\s*-crosses-the-newline bug"

# POSITIVE: the category vocabulary is closed.
fixture "${TMP}/d" "${DECLARED_BADCAT}"
expect_rc "$(run_rc "${TMP}/d")" 1 "invalid category fails"

# POSITIVE: the REVERSE shift breaks onlyMethods() doubles and must also fail.
fixture "${TMP}/e" "${MAGIC}" "${DECLARED_NO_TAG}"
expect_rc "$(run_rc "${TMP}/e")" 1 "undeclared declared->magic shift fails"

# NEGATIVE: a diff touching no contract file is EMPTY SCOPE, never a PASS.
fixture "${TMP}/f" "${MAGIC}" "${MAGIC}"
(
    cd "${TMP}/f" || exit 1
    mkdir -p lib/Other
    printf '<?php\nclass Other {}\n' > lib/Other/Other.php
    git add -A >/dev/null
    git commit -qm unrelated
) >/dev/null 2>&1
expect_rc "$(run_rc "${TMP}/f")" 3 "diff with no contract file reports empty scope, not pass"

# NEGATIVE: a repo publishing no contract is NOT APPLICABLE.
NOCONTRACT="${TMP}/g"
rm -rf "${NOCONTRACT}"; mkdir -p "${NOCONTRACT}/lib"
(
    cd "${NOCONTRACT}" || exit 1
    git init -q .
    git config user.email test@example.invalid
    git config user.name 'Gate Test'
    printf '<?php\nclass X {}\n' > lib/X.php
    git add -A >/dev/null
    git commit -qm base
    git commit -qm second --allow-empty
) >/dev/null 2>&1
expect_rc "$(run_rc "${NOCONTRACT}")" 4 "repo with no lib/Contract is not applicable"

# POSITIVE: an unresolvable base FAILS CLOSED. A broken scope must never be
# reported as an empty one — that is how a broken gate reads as a green gate.
python3 "${CHECKER}" "${TMP}/a" --base no-such-ref-exists >/dev/null 2>&1
expect_rc "$?" 1 "unresolvable base fails closed"

# WIRING: the terminal summary line the runner greps for must be printed, or
# the runner cannot tell a clean run from a crashed one.
out="$(python3 "${CHECKER}" "${TMP}/a" --base HEAD~1 2>&1 || true)"
if printf '%s' "${out}" | grep -qE '^checked [0-9]+ contract '; then
    ok "prints the terminal summary the runner asserts on"
else
    no "prints the terminal summary the runner asserts on" "got: ${out}"
fi

echo "  ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
