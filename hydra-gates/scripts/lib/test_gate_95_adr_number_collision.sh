#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_95_adr_number_collision.sh — gate-95 must see two documents
# claiming one ADR number, and must not invent a finding where none exists.
#
# WHAT THIS GUARDS
# ----------------
# Measured on hydra 2026-08-26: EIGHT numbers were each claimed by two or three
# documents — 037, 041, 049, 050, 051, 076, 081, 084 — over 18 files, with
# 1,640 citing files across 20 repositories. `ADR-081` resolved to three
# different decisions at once.
#
# The reason this needs a gate rather than a sweep is that the ambiguity is
# SILENT. Nothing errors while a citation key points at two documents; the
# reader simply follows it to the wrong one. The cost is paid later, when the
# citations can no longer be repaired mechanically because each has to be read
# to learn which document it meant.
#
# The anti-widening arms are the ones that earn their place. An ADR title
# legitimately cites OTHER ADRs — "# ADR-049: Declarative Widget Vocabulary
# (extends ADR-036)" — and a checker that takes the last match, or any match,
# rather than the first would report that file as a mismatch. Arm 4 pins it.
#
# ARMS
#   1  two files claiming one number is caught
#   2  three files claiming one number is caught, and counted as one finding
#   3  a title number disagreeing with its filename is caught  (half-renumber)
#   4  ANTI-WIDENING — a title citing a SECOND ADR is not a mismatch
#   5  ANTI-WIDENING — distinct numbers pass
#   6  a repo with no openspec/architecture is `na` (exit 4), not a pass
#   7  the terminal summary is printed on the passing path too — a gate that
#      prints nothing when it passes cannot be shown to have run

set -u

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_checker="${_here}/check_adr_number_collision.py"

_failures=0
_ok()  { echo "  ok   — $1"; }
_bad() { echo "  FAIL — $1"; _failures=$((_failures + 1)); }

_tmproot="$(mktemp -d)"
trap 'rm -rf "${_tmproot}"' EXIT

# _fixture <name> — makes an openspec/architecture dir, echoes its repo root.
_fixture() {
    local d="${_tmproot}/$1/openspec/architecture"
    mkdir -p "${d}"
    echo "${_tmproot}/$1"
}

# ---- arm 1: two documents, one number -------------------------------------
_r="$(_fixture two_claim_one)"
printf '# ADR-037: Canonical Requirement Heading Format\n' > "${_r}/openspec/architecture/adr-037-canonical-req-id-format.md"
printf '# ADR-037: Modular register and manifest fragments\n' > "${_r}/openspec/architecture/adr-037-modular-config-fragments.md"
_out="$(python3 "${_checker}" "${_r}" 2>&1)"; _rc=$?
if [ "${_rc}" -ne 0 ] && echo "${_out}" | grep -q 'ADR-037 is claimed by 2 documents'; then
    _ok "two documents claiming ADR-037 is caught"
else
    _bad "two documents claiming ADR-037 NOT caught (rc=${_rc}): ${_out}"
fi

# ---- arm 2: three documents, one number, one finding ----------------------
_r="$(_fixture three_claim_one)"
printf '# ADR-081: Adopt Vue 3 across the fleet\n' > "${_r}/openspec/architecture/adr-081-vue3-migration.md"
printf '# ADR-081: Money and effort have one home each\n' > "${_r}/openspec/architecture/adr-081-money-and-effort-ownership.md"
printf '# ADR-081: Public Surface Placement\n' > "${_r}/openspec/architecture/adr-081-public-surface-placement.md"
_out="$(python3 "${_checker}" "${_r}" 2>&1)"; _rc=$?
_n="$(echo "${_out}" | grep -c '^FAIL ')"
if [ "${_rc}" -ne 0 ] && echo "${_out}" | grep -q 'claimed by 3 documents' && [ "${_n}" -eq 1 ]; then
    _ok "three documents claiming ADR-081 is one finding naming all three"
else
    _bad "three-way collision mishandled (rc=${_rc}, findings=${_n}): ${_out}"
fi

# ---- arm 3: title/filename mismatch ---------------------------------------
_r="$(_fixture half_renumbered)"
printf '# ADR-041: Universal In-App Editing via OpenBuild\n' > "${_r}/openspec/architecture/adr-101-universal-in-app-editing.md"
_out="$(python3 "${_checker}" "${_r}" 2>&1)"; _rc=$?
if [ "${_rc}" -ne 0 ] && echo "${_out}" | grep -q 'filename says ADR-101 but its title says ADR-041'; then
    _ok "a half-finished renumber (title != filename) is caught"
else
    _bad "title/filename mismatch NOT caught (rc=${_rc}): ${_out}"
fi

# ---- arm 4: ANTI-WIDENING — a title citing a second ADR -------------------
_r="$(_fixture title_cites_another)"
printf '# ADR-049: Declarative Widget Vocabulary (extends ADR-036)\n' > "${_r}/openspec/architecture/adr-049-declarative-widget-vocabulary.md"
printf '# ADR-066: Narrow lifting of the ADR-041 moratorium\n' > "${_r}/openspec/architecture/adr-066-cross-app-leaf-registration.md"
_out="$(python3 "${_checker}" "${_r}" 2>&1)"; _rc=$?
if [ "${_rc}" -eq 0 ]; then
    _ok "a title citing a SECOND ADR is not reported as a mismatch"
else
    _bad "false positive on a title citing another ADR (rc=${_rc}): ${_out}"
fi

# ---- arm 5: ANTI-WIDENING — distinct numbers pass -------------------------
_r="$(_fixture all_distinct)"
printf '# ADR-037: Modular register and manifest fragments\n' > "${_r}/openspec/architecture/adr-037-modular-config-fragments.md"
printf '# ADR-038: Canonical Requirement Heading Format\n' > "${_r}/openspec/architecture/adr-038-canonical-req-id-format.md"
_out="$(python3 "${_checker}" "${_r}" 2>&1)"; _rc=$?
if [ "${_rc}" -eq 0 ]; then
    _ok "distinct numbers pass"
else
    _bad "false positive on distinct numbers (rc=${_rc}): ${_out}"
fi

# ---- arm 6: no ADRs at all is `na`, not a pass ----------------------------
_r="${_tmproot}/no_adrs"; mkdir -p "${_r}/src"
_out="$(python3 "${_checker}" "${_r}" 2>&1)"; _rc=$?
if [ "${_rc}" -eq 4 ]; then
    _ok "a repo with no openspec/architecture is na (exit 4), not a pass"
else
    _bad "expected exit 4 for a repo with no ADRs, got ${_rc}: ${_out}"
fi

# ---- arm 7: the terminal summary is printed when passing ------------------
_r="$(_fixture summary_on_pass)"
printf '# ADR-001: Data layer\n' > "${_r}/openspec/architecture/adr-001-data-layer.md"
_out="$(python3 "${_checker}" "${_r}" 2>&1)"; _rc=$?
if [ "${_rc}" -eq 0 ] && echo "${_out}" | grep -qE '^checked [0-9]+ ADR file'; then
    _ok "the terminal summary is printed on the passing path"
else
    _bad "no terminal summary on the passing path (rc=${_rc}): ${_out}"
fi

echo ""
if [ "${_failures}" -eq 0 ]; then
    echo "test_gate_95_adr_number_collision: all arms passed"
    exit 0
fi
echo "test_gate_95_adr_number_collision: ${_failures} arm(s) failed"
exit 1
