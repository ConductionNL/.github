#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# gate-116 (connections-declaration): acceptance over a REAL git history,
# through the real runner.
#
# A DELTA gate cannot be covered by a `gate-acceptance/` bundle: that format
# runs the runner against a plain directory with no git history, so the gate
# can only report NOT APPLICABLE there. Same reason gates 101, 108 and 114 have
# dedicated suites listed in COVERED-ELSEWHERE.md.
#
# The rule-by-rule arms live in test_check_connections_declaration.js. This
# suite pins what only the runner can get wrong: the verdict word, the scope,
# the per-repo promotion, and the fall-through with no base.
#
#   ARM 1  a duplicate key added by the change is a WARNING, named in the log
#   ARM 2  the WARNING reaches neither the FAIL lines nor the failure count
#   ARM 3  inherited debt: a base that already carries a defect, and a change
#          touching none of the rule's sides, is NOT APPLICABLE, not a WARNING
#   ARM 4  an anchor removed from src/ with the declaration untouched is still
#          judged, because rule 4 has two sides
#   ARM 5  a clean change PASSES and prints the census line
#   ARM 6  no delta base is NOT APPLICABLE, never PASS
#   ARM 7  HYDRA_GATE_CONNECTIONS_DECLARATION_BLOCKING=1 makes it FAIL
#   ARM 8  an app with no declaration is NOT APPLICABLE

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
RUNNER="${SCRIPT_DIR}/../run-hydra-gates.sh"

_fail_n=0
_ok()  { printf '  ok:   %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf '  FAIL: %s\n' "$1"; }

if ! node -e "require('ajv/dist/2020')" >/dev/null 2>&1 \
    && ! node -e "require.resolve('ajv/dist/2020', { paths: ['${SCRIPT_DIR}'] })" >/dev/null 2>&1; then
    echo "FAIL: Ajv is not resolvable, so gate-116 fails closed on every arm and this suite can assert nothing. Install ajv (CI: npm install ajv at the repo root) or set NODE_PATH."
    exit 1
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/gate116-scope.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT
APP="${WORK}/app"
mkdir -p "${APP}/appinfo" "${APP}/lib/Settings" "${APP}/src/views"

cat > "${APP}/appinfo/info.xml" <<'XML'
<?xml version="1.0"?>
<info>
    <id>fixture</id>
    <name>Fixture</name>
    <version>1.0.0</version>
</info>
XML

_declaration() {  # <extra-json-entry-or-empty>
    local _extra="${1:-}"
    cat <<JSON
{
  "app": "fixture",
  "connections": [
    { "key": "zgw", "title": "ZGW APIs", "order": 10, "settingsUrl": "/settings/admin/fixture#section-zgw" },
    { "key": "kvk", "title": "KvK", "available": false }${_extra:+,
    ${_extra}}
  ]
}
JSON
}

_settings_view() {  # <anchor-id>
    printf '<template>\n\t<NcSettingsSection id="%s" name="ZGW" />\n</template>\n' "$1"
}

cd "${APP}" || exit 1
git init --quiet .
git config user.email fixture@example.invalid
git config user.name Fixture

# ── base: a clean declaration.
_declaration > lib/Settings/connections.json
_settings_view section-zgw > src/views/AdminSettings.vue
echo "x" > README.md
git add -A && git commit --quiet -m "base, a clean declaration"
git branch -M base

# ── planted: the change adds a second zgw key.
git checkout --quiet -b planted
_declaration '{ "key": "zgw", "title": "ZGW again" }' > lib/Settings/connections.json
git add -A && git commit --quiet -m "a duplicate key"

# ── clean: the change adds a valid connection.
git checkout --quiet base
git checkout --quiet -b clean
_declaration '{ "key": "brp", "title": "BRP", "order": 80 }' > lib/Settings/connections.json
git add -A && git commit --quiet -m "one more connection"

# ── anchor-gone: the settings section is renamed, the declaration untouched.
git checkout --quiet base
git checkout --quiet -b anchor-gone
_settings_view section-zaakgericht > src/views/AdminSettings.vue
git add -A && git commit --quiet -m "rename the settings section"

# ── debt-base: a base that already carries a defect (a mismatched app id),
#    and a change that touches only the README.
git checkout --quiet base
git checkout --quiet -b debt-base
sed 's/"app": "fixture"/"app": "someoneelse"/' lib/Settings/connections.json > lib/Settings/c.tmp \
    && mv lib/Settings/c.tmp lib/Settings/connections.json
git add -A && git commit --quiet -m "inherited debt: a mismatched app id"
git checkout --quiet -b unrelated
echo "y" >> README.md
git add -A && git commit --quiet -m "an unrelated change"

_run() {  # <branch> [extra runner args...]
    local _b="$1"; shift
    git checkout --quiet "${_b}"
    mkdir -p "${WORK}/logs-${_b}"
    HYDRA_GATE_LOG_DIR="${WORK}/logs-${_b}" bash "${RUNNER}" "$@" "${APP}" 2>&1
}

_verdict() {
    printf '%s\n' "$1" | grep -E '^\[gate-116\] connections-declaration: (PASS|FAIL|WARNING|SKIPPED|NOT APPLICABLE)' | head -1
}

echo "-- ARM 1: a duplicate key added by the change is a WARNING, and it is named --"
_out_planted="$(_run planted --base base)"
_v="$(_verdict "${_out_planted}")"
case "${_v}" in
    *WARNING*) _ok "gate-116 reports WARNING on a duplicate key" ;;
    *)         _bad "expected WARNING on the planted branch, got: ${_v:-<no gate-116 verdict line>}" ;;
esac
if grep -q 'key "zgw" is used by connections\[0\] and connections\[2\]' "${WORK}/logs-planted/hydra-gate-connections-declaration.log" 2>/dev/null; then
    _ok "the log names the key and both positions"
else
    _bad "the log does not name the duplicate: $(head -3 "${WORK}/logs-planted/hydra-gate-connections-declaration.log" 2>/dev/null | tr '\n' ' ')"
fi

_out_clean="$(_run clean --base base)"
_clean_fails="$(printf '%s\n' "${_out_clean}" | grep -cE '^\[gate-[0-9]+\] [a-z0-9-]+: FAIL' || true)"

echo "-- ARM 2: the WARNING does not block --"
if printf '%s\n' "${_out_planted}" | grep -qE '^\[gate-116\] connections-declaration: FAIL'; then
    _bad "gate-116 printed FAIL while shipping advisory; this package resolves at @main for 21 repos"
else
    _ok "gate-116 never printed a FAIL verdict on the planted branch"
fi
_planted_fails="$(printf '%s\n' "${_out_planted}" | grep -cE '^\[gate-[0-9]+\] [a-z0-9-]+: FAIL' || true)"
if [ "${_planted_fails}" = "${_clean_fails}" ]; then
    _ok "the planted branch carries as many FAIL lines as the clean one (${_planted_fails}), so the warning added none"
else
    _bad "the planted branch has ${_planted_fails} FAIL line(s) and the clean branch ${_clean_fails}; the advisory leaked into the failure count"
fi

echo "-- ARM 3: inherited debt is not this change's problem --"
_v="$(_verdict "$(_run unrelated --base debt-base)")"
case "${_v}" in
    *"NOT APPLICABLE"*) _ok "a change touching no side of a rule is not judged, though the base carries a mismatched app id" ;;
    *)                  _bad "expected NOT APPLICABLE on a README-only change, got: ${_v:-<no verdict>}" ;;
esac

echo "-- ARM 4: an anchor removed from src/ is judged, the declaration untouched --"
_v="$(_verdict "$(_run anchor-gone --base base)")"
case "${_v}" in
    *WARNING*) _ok "renaming the settings section warns, though connections.json did not change" ;;
    *)         _bad "expected WARNING when the anchor disappeared, got: ${_v:-<no verdict>}" ;;
esac
if grep -q 'links to #section-zgw, and no file under src/ or templates/ defines that anchor' "${WORK}/logs-anchor-gone/hydra-gate-connections-declaration.log" 2>/dev/null; then
    _ok "the log names the missing anchor"
else
    _bad "the log does not name #section-zgw"
fi

echo "-- ARM 5: a clean change passes and shows it read the file --"
_v="$(_verdict "${_out_clean}")"
case "${_v}" in
    *PASS*) _ok "a valid new connection passes" ;;
    *)      _bad "expected PASS on the clean branch, got: ${_v:-<no verdict>}" ;;
esac
case "${_out_clean}" in
    *"[gate-116] [connections-declaration] checked 1 declaration file(s), 0 finding(s)"*) _ok "the census line is on stdout, so the PASS can be shown to have read the file" ;;
    *) _bad "no census line on stdout for the clean branch" ;;
esac

echo "-- ARM 6: no delta base is NOT APPLICABLE, never PASS --"
_v="$(_verdict "$(_run planted --full)")"
case "${_v}" in
    *"NOT APPLICABLE"*) _ok "with no base the gate says it had nothing to judge" ;;
    *)                  _bad "expected NOT APPLICABLE with no base, got: ${_v:-<no verdict>}" ;;
esac

echo "-- ARM 7: a repo can opt in to blocking --"
_v="$(_verdict "$(HYDRA_GATE_CONNECTIONS_DECLARATION_BLOCKING=1 _run planted --base base)")"
case "${_v}" in
    *FAIL*) _ok "HYDRA_GATE_CONNECTIONS_DECLARATION_BLOCKING=1 makes the same finding block" ;;
    *)      _bad "the per-repo opt-in did not promote the finding: ${_v:-<no verdict>}" ;;
esac

echo "-- ARM 8: an app with no declaration is NOT APPLICABLE --"
git checkout --quiet base
git checkout --quiet -b no-declaration
git rm --quiet lib/Settings/connections.json
echo "z" >> README.md
git add -A && git commit --quiet -m "no declaration"
_v="$(_verdict "$(_run no-declaration --base base)")"
case "${_v}" in
    *"NOT APPLICABLE"*) _ok "no lib/Settings/connections.json is NOT APPLICABLE" ;;
    *)                  _bad "expected NOT APPLICABLE with no declaration, got: ${_v:-<no verdict>}" ;;
esac

echo ""
if [ "${_fail_n}" -eq 0 ]; then
    echo "gate-116 connections-declaration acceptance: all arms passed."
    exit 0
fi
echo "gate-116 connections-declaration acceptance: ${_fail_n} arm(s) failed."
exit 1
