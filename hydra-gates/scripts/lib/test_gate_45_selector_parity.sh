#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_45_selector_parity.sh — gate-45 must judge the SELECTORS that carry
# motion, not the presence of a reduced-motion block somewhere in the file.
#
# WHAT THIS GUARDS (thematiq#604, 2026-09-17)
# --------------------------------------------
# Until 2026-09-21 the checker asked one question per file: is there a
# `@media (prefers-reduced-motion …)` block in it? thematiq's
# css/systems/nldesign/theme.css had one, so the gate said PASS — at `6dcbbaf9`,
# where `c495c99c` had added `:not(.action-button)` to four `!important` motion
# selectors while the reset kept the bare `.button-vue, button, .button`. Equal
# specificity before (reset wins on source order); strictly less after (reset
# loses on every button). The gate said PASS again at `67caeb85`, after the
# selectors were mirrored back.
#
# Measured 2026-09-21 with the package runner at full scope, one variable:
#   theme.css @ 6dcbbaf9  (reset no longer names the motion selectors)  PASS  <- the defect
#   theme.css @ 67caeb85  (reset names them again)                      PASS
#
# Same verdict on the broken and the fixed file: the gate did not observe the
# property it is named after. The arms below are that file's shape reduced to
# its cascade essentials, plus the anti-widening controls for every correct
# idiom the fleet writes — the change turns a file-level question into a
# per-selector one, and that is precisely the kind of change that turns a gate
# into a noise generator if the controls are not pinned.
#
#   P1  the thematiq shape: !important motion on `.btn:not(.x)`, reset on bare `.btn` → FAIL, names the selector
#   P2  CONTROL: the same file with the reset mirroring the selectors                → PASS
#   P3  a LESS specific guard covers a plain motion when the guard is !important    → PASS  (.card covers .card:hover)
#   P3b …and does NOT when both are plain: `.card:hover` beats `.card` by specificity → FAIL
#   P4  a universal `*` reset covers plain motion (ARM 6 of the scope suite)         → PASS
#   P4b …and does NOT cover !important motion: `*` has specificity 0                  → FAIL
#   P5  `@media (prefers-reduced-motion: no-preference) { …motion… }` is guarded by construction → PASS
#   P6  a duration token zeroed inside the reduced-motion block covers its users    → PASS
#   P7  the markup arm judges per selector too: a scoped <style> guarding `.other` does not guard `.m` → FAIL; guarding `.m` → PASS
#   P8  SCSS nesting: `&:hover` resolves against its parent before matching          → PASS / FAIL
#   P9  `:is(.a, .b)` keeps its comma — the selector is matched whole                 → PASS
#   P10 `html .btn` (ancestor boost) is a MORE specific guard for `.btn`              → PASS
#   P11 the repo-wide universal reset in ANOTHER file covers plain motion, not !important motion → PASS / FAIL

set -u

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_scripts="$(cd "${_here}/.." && pwd)"
_runner="${HYDRA_GATES_RUNNER_UNDER_TEST:-${_scripts}/run-hydra-gates.sh}"

_failures=0
_ok()  { echo "  ok   — $1"; }
_bad() { echo "  FAIL — $1"; _failures=$((_failures + 1)); }

echo "test_gate_45_selector_parity.sh"

_tmp="$(mktemp -d "${TMPDIR:-/tmp}/hydra-g45-parity.XXXXXX")"
trap 'rm -rf "${_tmp}"' EXIT

_mkapp() {  # _mkapp <dir> — an app with a css/ and a CLEAN .vue
    mkdir -p "$1/css" "$1/src"
    printf '{"name":"fx","menu":[]}\n' > "$1/src/manifest.json"
    cat > "$1/src/Clean.vue" <<'VUE'
<template>
	<div class="x">hi</div>
</template>
<script>
export default { name: 'Clean' }
</script>
<style scoped>
.x { color: red; }
</style>
VUE
    (
        cd "$1" || exit 1
        git init -q .
        git add -A
        git -c user.email=t@t -c user.name=t commit -qm init
    ) >/dev/null 2>&1
}

# Written to a FILE, not a variable: `$(_run45 …)` is a subshell and an
# assignment made inside it never reaches the caller.
_LAST_LOG_PTR="${_tmp}/last-log-path"
_run45() {  # _run45 <appdir> -> echoes the gate-45 verdict line
    local logs="${_tmp}/logs.$$.${RANDOM}"
    mkdir -p "${logs}"
    printf '%s' "${logs}/hydra-gate-prefers-reduced-motion.log" > "${_LAST_LOG_PTR}"
    (
        cd "$1" || exit 1
        git add -A >/dev/null 2>&1
        git -c user.email=t@t -c user.name=t commit -qm wip >/dev/null 2>&1
        HYDRA_GATE_LOG_DIR="${logs}" bash "${_runner}" . 2>/dev/null
    ) | grep -E '^\[gate-45\]' || true
}

_assert() {  # _assert <label> <expected-substring> <actual>
    case "$3" in
        *"$2"*) _ok "$1" ;;
        *)      _bad "$1 — got: $3" ;;
    esac
}

_log_has() {  # _log_has <label> <substring> — the finding must NAME the selector
    if grep -qF -- "$2" "$(cat "${_LAST_LOG_PTR}")" 2>/dev/null; then
        _ok "$1"
    else
        _bad "$1 — log does not contain '$2': $(cat "$(cat "${_LAST_LOG_PTR}")" 2>/dev/null)"
    fi
}

# ---------------------------------------------------------------------------
# P1 — the thematiq shape. This is theme.css:419 and :1024 at 6dcbbaf9 with the
# non-button selectors removed; the file's own comment above the reset block
# explains why `*` was not an option and why the selectors must be repeated.
# ---------------------------------------------------------------------------
_app="${_tmp}/p1"
_mkapp "${_app}"
cat > "${_app}/css/theme.css" <<'CSS'
.button-vue:not(.action-button),
.button-vue:not(.action-button) .button-vue__text,
button:not(.action-button),
.button {
	transition:
		background-color var(--nldesign-animation-quick) ease,
		border-color var(--nldesign-animation-quick) ease,
		color var(--nldesign-animation-quick) ease !important;
}

/* Every motion declaration in this file is `!important` and carries class- or
   attribute-level specificity. A universal `*` reset therefore does NOT
   override them. So the selectors are repeated verbatim below — equal
   specificity, later in source order. Keep this block in step. */
@media (prefers-reduced-motion: reduce) {
	.button-vue,
	button,
	.button {
		transition: none !important;
		animation: none !important;
	}
}
CSS
_assert "P1  reset that stopped naming the !important motion selectors → FAIL" "FAIL" "$(_run45 "${_app}")"
_log_has "P1  the finding names the uncovered selector" "selector=.button-vue:not(.action-button)"
_log_has "P1  …and the descendant one" "selector=.button-vue:not(.action-button) .button-vue__text"
_log_has "P1  …and the bare-element one" "selector=button:not(.action-button)"
if grep -qF -- "selector=.button " "$(cat "${_LAST_LOG_PTR}")" 2>/dev/null || grep -qE -- 'selector=\.button$' "$(cat "${_LAST_LOG_PTR}")" 2>/dev/null; then
    _bad "P1  .button IS covered by the reset and must not be reported"
else
    _ok "P1  .button, which the reset still names, is not reported"
fi

# P2 — CONTROL. Same file, reset mirrors the selectors (this is 67caeb85's shape).
_app="${_tmp}/p2"
_mkapp "${_app}"
cat > "${_app}/css/theme.css" <<'CSS'
.button-vue:not(.action-button),
.button-vue:not(.action-button) .button-vue__text,
button:not(.action-button),
.button {
	transition: background-color 0.2s ease, color 0.2s ease !important;
}
@media (prefers-reduced-motion: reduce) {
	.button-vue:not(.action-button),
	.button-vue:not(.action-button) .button-vue__text,
	button:not(.action-button),
	.button {
		transition: none !important;
		animation: none !important;
	}
}
CSS
_assert "P2  control: the reset names every motion selector → PASS" "PASS" "$(_run45 "${_app}")"

# ---------------------------------------------------------------------------
# P3 — importance beats specificity: a plain `.card:hover` motion is overridden
# by `.card { transition: none !important }` even though `.card` is less specific.
# ---------------------------------------------------------------------------
_app="${_tmp}/p3"
_mkapp "${_app}"
cat > "${_app}/css/card.css" <<'CSS'
.card:hover { transition: box-shadow 0.3s ease; }
@media (prefers-reduced-motion: reduce) {
	.card { transition: none !important; }
}
CSS
_assert "P3  a less specific !important guard covers a plain motion → PASS" "PASS" "$(_run45 "${_app}")"

# P3b — and with both plain, `.card:hover` (0,2,0) beats `.card` (0,1,0): the
# motion stays on screen with the fallback right there in the file.
_app="${_tmp}/p3b"
_mkapp "${_app}"
cat > "${_app}/css/card.css" <<'CSS'
.card:hover { transition: box-shadow 0.3s ease; }
@media (prefers-reduced-motion: reduce) {
	.card { transition: none; }
}
CSS
_assert "P3b a less specific PLAIN guard does not cover a more specific plain motion → FAIL" "FAIL" "$(_run45 "${_app}")"

# ---------------------------------------------------------------------------
# P4 — the universal reset: covers plain motion (ARM 6 of the scope suite,
# unchanged), covers NO !important motion (`*` has specificity 0).
# ---------------------------------------------------------------------------
_app="${_tmp}/p4"
_mkapp "${_app}"
cat > "${_app}/css/main.css" <<'CSS'
.spinner { animation: spin 1s linear infinite; }
.btn { transition: background-color 0.3s ease; }
@media (prefers-reduced-motion: reduce) {
	*, *::before, *::after {
		animation-duration: 0.01ms !important;
		transition-duration: 0.01ms !important;
	}
}
CSS
_assert "P4  a universal !important reset covers plain motion → PASS" "PASS" "$(_run45 "${_app}")"

_app="${_tmp}/p4b"
_mkapp "${_app}"
cat > "${_app}/css/main.css" <<'CSS'
.spinner { animation: spin 1s linear infinite !important; }
@media (prefers-reduced-motion: reduce) {
	*, *::before, *::after {
		animation-duration: 0.01ms !important;
		transition-duration: 0.01ms !important;
	}
}
CSS
_assert "P4b a universal reset does NOT cover an !important motion → FAIL" "FAIL" "$(_run45 "${_app}")"
_log_has "P4b the finding says why" "(!important"

# ---------------------------------------------------------------------------
# P5 — the inverse idiom: motion that only exists when motion is wanted.
# ---------------------------------------------------------------------------
_app="${_tmp}/p5"
_mkapp "${_app}"
cat > "${_app}/css/main.css" <<'CSS'
@media (prefers-reduced-motion: no-preference) {
	.drawer { transition: transform 0.3s ease; }
	.spinner { animation: spin 1s linear infinite; }
}
CSS
_assert "P5  motion declared inside no-preference is guarded by construction → PASS" "PASS" "$(_run45 "${_app}")"

# ---------------------------------------------------------------------------
# P6 — the duration-token convention (atom-design): the reduced-motion block
# zeroes the token every motion declaration reads, and names no selector.
# ---------------------------------------------------------------------------
_app="${_tmp}/p6"
_mkapp "${_app}"
cat > "${_app}/css/tokens.css" <<'CSS'
:root { --am-dur: 300ms; }
.mock { transition: opacity var(--am-dur) ease; }
.mock__bar { animation: slide var(--am-dur) linear infinite; }
@media (prefers-reduced-motion: reduce) {
	:root { --am-dur: 0ms; }
}
CSS
_assert "P6  a duration token zeroed in the reduced-motion block covers its users → PASS" "PASS" "$(_run45 "${_app}")"

# ---------------------------------------------------------------------------
# P7 — the markup arm judges per selector too.
# ---------------------------------------------------------------------------
_vue_with_guard() {  # _vue_with_guard <appdir> <guard-selector>
    cat > "$1/src/Motion.vue" <<VUE
<template>
	<div class="m">hi</div>
</template>
<script>
export default { name: 'Motion' }
</script>
<style scoped>
.m { transition: opacity 0.4s ease; }
@media (prefers-reduced-motion: reduce) {
	$2 { transition: none; }
}
</style>
VUE
}
_app="${_tmp}/p7a"
_mkapp "${_app}"
_vue_with_guard "${_app}" ".other"
_assert "P7  a <style> block guarding .other does not guard .m → FAIL" "FAIL" "$(_run45 "${_app}")"
_log_has "P7  the finding is attributed to the <style> block" "<style> rule=motion-selector-not-overridden"

_app="${_tmp}/p7b"
_mkapp "${_app}"
_vue_with_guard "${_app}" ".m"
_assert "P7b the same block guarding .m → PASS" "PASS" "$(_run45 "${_app}")"

# ---------------------------------------------------------------------------
# P8 — SCSS nesting: `&:hover` is `.btn:hover`, and is matched as such.
# ---------------------------------------------------------------------------
_scss_app() {  # _scss_app <appdir> <guard-selector>
    mkdir -p "$1/src/styles"
    cat > "$1/src/styles/btn.scss" <<SCSS
.btn {
	color: red;
	&:hover { transition: background-color 0.2s ease; }
}
@media (prefers-reduced-motion: reduce) {
	$2 { transition: none; }
}
SCSS
}
_app="${_tmp}/p8a"
_mkapp "${_app}"
_scss_app "${_app}" ".btn:hover"
_assert "P8  nested &:hover resolves to .btn:hover and matches the guard → PASS" "PASS" "$(_run45 "${_app}")"

_app="${_tmp}/p8b"
_mkapp "${_app}"
_scss_app "${_app}" ".btn"
_assert "P8b a plain .btn guard does not override the more specific .btn:hover → FAIL" "FAIL" "$(_run45 "${_app}")"
_log_has "P8b the resolved selector is what gets reported" "selector=.btn:hover"

# ---------------------------------------------------------------------------
# P9 — a comma inside :is() / :not() is not a selector separator.
# ---------------------------------------------------------------------------
_app="${_tmp}/p9"
_mkapp "${_app}"
cat > "${_app}/css/is.css" <<'CSS'
.x:is(.a, .b) { transition: color 0.2s ease; }
@media (prefers-reduced-motion: reduce) {
	.x:is(.a, .b) { transition: none; }
}
CSS
_assert "P9  :is(.a, .b) is matched whole → PASS" "PASS" "$(_run45 "${_app}")"

# ---------------------------------------------------------------------------
# P10 — the ancestor boost: `html .btn` is more specific than `.btn`, so it
# overrides even an !important motion when it is !important itself.
# ---------------------------------------------------------------------------
_app="${_tmp}/p10"
_mkapp "${_app}"
cat > "${_app}/css/boost.css" <<'CSS'
.btn { transition: color 0.2s ease !important; }
@media (prefers-reduced-motion: reduce) {
	html .btn { transition: none !important; }
}
CSS
_assert "P10 an html-prefixed !important guard covers an !important motion → PASS" "PASS" "$(_run45 "${_app}")"

# ---------------------------------------------------------------------------
# P11 — the repo-wide universal reset (pre-pass flag) is a `*` guard, not an
# exemption: it covers plain motion in another file and no !important motion.
# ---------------------------------------------------------------------------
_reset_file() {
    cat > "$1/css/reset.css" <<'CSS'
@media (prefers-reduced-motion: reduce) {
	*, *::before, *::after {
		animation-duration: 0.01ms !important;
		transition-duration: 0.01ms !important;
	}
}
CSS
}
_app="${_tmp}/p11a"
_mkapp "${_app}"
_reset_file "${_app}"
printf '.spinner { animation: spin 1s linear infinite; }\n' > "${_app}/css/motion.css"
_assert "P11 a universal reset in another file covers plain motion elsewhere → PASS" "PASS" "$(_run45 "${_app}")"

_app="${_tmp}/p11b"
_mkapp "${_app}"
_reset_file "${_app}"
printf '.spinner { animation: spin 1s linear infinite !important; }\n' > "${_app}/css/motion.css"
_assert "P11b …and does not cover !important motion elsewhere → FAIL" "FAIL" "$(_run45 "${_app}")"
_log_has "P11b the finding lands on the motion file, not the reset" "css/motion.css"

echo ""
if [ "${_failures}" -eq 0 ]; then
    echo "test_gate_45_selector_parity.sh: ALL GREEN"
    exit 0
fi
echo "test_gate_45_selector_parity.sh: ${_failures} FAILURE(S)"
exit 1
