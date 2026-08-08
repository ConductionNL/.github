#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_a11y_helper_wiring.sh — a broken a11y helper must report SKIPPED,
# never PASS, and must never take the rest of the run down with it.
#
# WHY THIS EXISTS
# ---------------
# gates 37 and 43 were moved out of the runner into python helpers. Both call
# sites started life as:
#
#     python3 "${helper}" "${files[@]}" >> "${log}" 2>/dev/null || true
#
# which discards the traceback AND the failure. A helper that crashes leaves an
# empty findings log, and an empty findings log is how these gates spell PASS —
# a falsely-green gate manufactured by its own plumbing, which is exactly the
# defect #147 was filed for and gate-19 (#249) was re-plumbed for.
#
# The second failure mode is worse and less obvious. gate-19's block turns
# `set -e` ON and leaves it on for every gate after it, though this script's
# header sets only `set -u`. With errexit live, a non-zero helper does not
# reach its own `_skip` — it kills the entire runner mid-sweep. When this was
# first measured on gate-38, 21 later gates went silently unreported and the
# run ended on the abort guard. So each case below asserts BOTH that the gate
# says SKIPPED and that the run still reached its COVERAGE summary.
#
# Run: bash scripts/lib/test_gate_a11y_helper_wiring.sh   (exit 0 = green)
set -uo pipefail

PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"

_fail_n=0
_pass_n=0
_ok()  { _pass_n=$((_pass_n + 1)); printf 'PASS — %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf 'FAIL — %s\n' "$1"; }

# A minimal app tree with something for each gate to find, so "no finding" can
# never be confused with "nothing to look at".
_APP="$(mktemp -d "${TMPDIR:-/tmp}/hydra-a11y-app.XXXXXXXX")" || exit 1
mkdir -p "${_APP}/src" "${_APP}/lib" "${_APP}/appinfo"
cat > "${_APP}/src/Thing.vue" <<'VUE'
<template>
	<div>
		<div tabindex="0" aria-hidden="true">unreachable-but-tabbable</div>
		<table>
			<tr><th>Name</th><th>Size</th></tr>
			<tr><td>a</td><td>1</td></tr>
		</table>
	</div>
</template>
VUE

_STAGE=""
_stage() {   # copy the package so a helper can be broken without touching it
    _STAGE="$(mktemp -d "${TMPDIR:-/tmp}/hydra-a11y-pkg.XXXXXXXX")" || return 1
    cp -r "${PKG_ROOT}/scripts" "${_STAGE}/scripts" || return 1
    return 0
}

_verdict() {  # <gate-n> -> echoes the gate's verdict line
    local _logdir _out
    _logdir="$(mktemp -d "${TMPDIR:-/tmp}/hydra-a11y-log.XXXXXXXX")"
    _out="$(HYDRA_GATE_LOG_DIR="${_logdir}" bash "${_STAGE}/scripts/run-hydra-gates.sh" "${_APP}" 2>&1 || true)"
    printf '%s' "${_out}"
    rm -rf "${_logdir}"
}

_check() {  # <gate-n> <gate-name> <how-broken> <out>
    local _n="$1" _name="$2" _how="$3" _out="$4" _line
    _line="$(printf '%s' "${_out}" | grep -E "^\[gate-${_n}\] " | head -1)"
    case "${_line}" in
        *"SKIPPED"*) _ok "gate-${_n} ${_name}: a ${_how} helper reports SKIPPED" ;;
        *": PASS"*)  _bad "gate-${_n} ${_name}: a ${_how} helper reported PASS having inspected NOTHING — ${_line}" ;;
        "")          _bad "gate-${_n} ${_name}: a ${_how} helper produced NO verdict line at all (did the run abort?)" ;;
        *)           _bad "gate-${_n} ${_name}: wanted SKIPPED, got — ${_line}" ;;
    esac
    # The run must still finish. An aborted run's PASS lines read exactly like
    # a clean run's, so "did not abort" is a separate assertion from "SKIPPED".
    if printf '%s' "${_out}" | grep -q '^\[hydra-gates\] COVERAGE:'; then
        _ok "gate-${_n} ${_name}: the run still reached its summary — later gates were not lost"
    else
        _bad "gate-${_n} ${_name}: the run ABORTED — a ${_how} helper took the whole sweep down"
    fi
}

echo "== gate-37 / gate-43 helper wiring =="
echo

# ---------------------------------------------------------------------------
# 0. POSITIVE CONTROL. With both helpers intact the fixture app must FAIL both
#    gates. Every assertion below is only meaningful because these fire.
# ---------------------------------------------------------------------------
if _stage; then
    _out="$(_verdict)"
    for _g in 37 43; do
        _line="$(printf '%s' "${_out}" | grep -E "^\[gate-${_g}\] " | head -1)"
        case "${_line}" in
            *": FAIL"*) _ok "positive control: gate-${_g} FAILS on the fixture app — ${_line%%—*}" ;;
            *) _bad "positive control: gate-${_g} did not fail on a fixture built to fail it — ${_line:-<none>}" ;;
        esac
    done
    rm -rf "${_STAGE}"
else
    _bad "could not stage the package — nothing below ran"
fi

# ---------------------------------------------------------------------------
# 1. MISSING helper (#147).
# ---------------------------------------------------------------------------
for _case in "37:aria-hidden-focusable:check_aria_hidden_focusable.py" \
             "43:table-headers:check_table_headers.py"; do
    _n="${_case%%:*}"; _rest="${_case#*:}"; _name="${_rest%%:*}"; _file="${_rest#*:}"
    if _stage; then
        rm -f "${_STAGE}/scripts/lib/${_file}"
        _check "${_n}" "${_name}" "MISSING" "$(_verdict)"
        rm -rf "${_STAGE}"
    fi
done

# ---------------------------------------------------------------------------
# 2. CRASHING helper (#249). Present, importable path, dies on invocation.
#    This is the case `2>/dev/null || true` could not tell from "no findings".
# ---------------------------------------------------------------------------
for _case in "37:aria-hidden-focusable:check_aria_hidden_focusable.py" \
             "43:table-headers:check_table_headers.py"; do
    _n="${_case%%:*}"; _rest="${_case#*:}"; _name="${_rest%%:*}"; _file="${_rest#*:}"
    if _stage; then
        printf 'raise SystemExit("boom")\n' > "${_STAGE}/scripts/lib/${_file}"
        _check "${_n}" "${_name}" "CRASHING" "$(_verdict)"
        rm -rf "${_STAGE}"
    fi
done

rm -rf "${_APP}"

echo
echo "== summary =="
printf '   passed: %d\n   failed: %d\n' "${_pass_n}" "${_fail_n}"
[ "${_fail_n}" -eq 0 ] || exit 1
echo
echo "ALL wiring assertions held."
