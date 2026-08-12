#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_gate_diff_provenance.sh — a diff-derived verdict must say WHICH diff.
#
# WHAT THIS GUARDS
# ----------------
# Two gates return a verdict computed from a diff, and neither said so in a
# place the reader could see. That is not a cosmetic complaint: a verdict whose
# scope is unstated cannot be checked, and an unfalsifiable reason is how the
# `.github#347` defect stood fleet-wide for weeks.
#
#   gate-61  passes `--base "${BASE_REF}"` UNCONDITIONALLY, which is deliberate
#            (it is always diff-scoped, ADR-078/ADR-020). But `bin/hydra-gates`
#            forwards no base on `--full`, so BASE_REF there is the RUNNER'S OWN
#            DEFAULT — while the run's preamble has already announced that there
#            is no base at all. `#371` fixed the empty-scope REASON and left
#            this: when the head commit DOES touch a listener, the default
#            resolves, the diff is real, and the gate BLOCKS the build under a
#            header saying no diff was computed.
#
#            Measured 2026-08-12, `--full` both times, one tree, only the head
#            commit varying:
#              head touches the listener  -> FAIL — 1 post-event listener(s)
#              head touches only docs     -> NOT APPLICABLE — computed NO diff
#            Two different answers from one tree prove the verdict is
#            diff-derived. The preamble denies the diff exists.
#
#   gate-54  checks (a) and (c)-(f) are FILE-scoped by design — a banned
#            dialect anywhere in a register you edited is yours to fix — so a
#            ONE-LINE RETITLE inherits every finding in the file. That design
#            is kept. What was missing is that the output said nothing about
#            it, so a defect the author wrote and a defect they stood next to
#            printed the identical sentence, and a fleet sweep saw
#            byte-identical base-and-head findings with no way to rank them.
#
# THE ANTI-WEAKENING ARM IS THE POINT. Both fixes are about what a verdict
# SAYS, and the cheapest way to make a verdict readable is to stop emitting it.
# So every arm below pairs its provenance assertion with a count assertion: the
# inherited finding must still BLOCK, and the listener FAIL must still be a
# FAIL. A run that got quieter fails this suite.
#
# Run: bash scripts/lib/test_gate_diff_provenance.sh

set -u

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_scripts="$(cd "${_here}/.." && pwd)"
_runner="${HYDRA_GATES_RUNNER_UNDER_TEST:-${_scripts}/run-hydra-gates.sh}"
_bin="${_scripts}/../bin/hydra-gates"

_failures=0
_ok()  { echo "  ok   — $1"; }
_bad() { echo "  FAIL — $1"; _failures=$((_failures + 1)); }

echo "test_gate_diff_provenance.sh"

_tmp="$(mktemp -d "${TMPDIR:-/tmp}/hydra-provenance.XXXXXX")"
trap 'rm -rf "${_tmp}"' EXIT

_git_c() { git -c user.email=t@t -c user.name=t "$@"; }

# ---------------------------------------------------------------------------
# gate-61 — a verdict on a --full run must name the base it judged against.
#
# `git init -b` is NOT used: it needs git >= 2.28 and this suite must not
# silently build a non-repository on an older git, where `_enum_tracked` falls
# back to `find`, every plant looks untracked, and the arms pass for the wrong
# reason. `symbolic-ref` works everywhere.
# ---------------------------------------------------------------------------
_mk61() {  # <dir> <touch-listener:yes|no>
    local _d="$1" _touch="$2"
    mkdir -p "${_d}/lib/AppInfo" "${_d}/lib/Listener" "${_d}/appinfo"
    printf '<?xml version="1.0"?>\n<info>\n <id>lwp</id>\n</info>\n' \
        > "${_d}/appinfo/info.xml"
    cat > "${_d}/lib/AppInfo/Application.php" <<'PHP'
<?php

namespace OCA\Lwp\AppInfo;

use OCA\Lwp\Listener\ThingCreatedListener;
use OCA\OpenRegister\Event\ObjectCreatedEvent;
use OCP\AppFramework\App;
use OCP\AppFramework\Bootstrap\IRegistrationContext;

class Application extends App {
    public function register(IRegistrationContext $context): void {
        $context->registerEventListener(ObjectCreatedEvent::class, ThingCreatedListener::class);
    }
}
PHP
    cat > "${_d}/lib/Listener/ThingCreatedListener.php" <<'PHP'
<?php

namespace OCA\Lwp\Listener;

use OCP\EventDispatcher\Event;
use OCP\EventDispatcher\IEventListener;

class ThingCreatedListener implements IEventListener {
    public function handle(Event $event): void {
        $client = $this->clientService->newClient();
        $client->post('https://example.invalid/hook', ['body' => 'x']);
        $this->objectService->saveObject('audit', ['event' => 'created']);
    }
}
PHP
    (
        cd "${_d}" || exit 1
        git init -q .
        git symbolic-ref HEAD refs/heads/development
        git add -A
        _git_c commit -qm "base — the listener and its debt already exist here"
        # origin/development points at the BASE commit, as in CI.
        git update-ref refs/remotes/origin/development HEAD
    ) >/dev/null 2>&1
    if [ "${_touch}" = "yes" ]; then
        printf '\n// touched by the head commit\n' \
            >> "${_d}/lib/Listener/ThingCreatedListener.php"
    else
        echo "docs" > "${_d}/NOTES.md"
    fi
    (
        cd "${_d}" || exit 1
        git add -A
        _git_c commit -qm "head"
    ) >/dev/null 2>&1
}

if [ ! -f "${_bin}" ]; then
    _bad "bin/hydra-gates not found at ${_bin} — the --full path cannot be exercised"
else
    _a61="${_tmp}/lwp-touched"
    _mk61 "${_a61}" yes
    _l61="${_tmp}/lwp-logs"; mkdir -p "${_l61}"
    _o61="${_tmp}/lwp-full.txt"
    ( cd "${_a61}" || exit 1
      HYDRA_GATE_LOG_DIR="${_l61}" bash "${_bin}" --full > "${_o61}" 2>&1 )

    # THE CONTROL FIRST: this must be a --full run, or nothing below is about
    # the defect. An arm that silently ran diff-scoped would pass trivially.
    # Reads SCOPE-MODE, not the old 'Base ref: n/a' string. Under the
    # full-scope-by-default change (#378) the preamble was reworded AND the two
    # facts came apart: a run is now full-scope independently of whether a
    # delta base resolved, so "reports no base" no longer means "is full-scope".
    # This control only ever wanted the latter.
    if grep -qE '^\[hydra-gates\] SCOPE-MODE: full' "${_o61}"; then
        _ok "control: the run really is full-scope (its preamble states SCOPE-MODE: full)"
    else
        _bad "control FAILED: this run is not full-scope — the gate-61 assertions below prove nothing"
    fi

    # ANTI-WEAKENING: the verdict itself must not have gone soft.
    if grep -qE '^\[gate-61\][^:]*: FAIL — [0-9]+ post-event listener' "${_o61}"; then
        _ok "gate-61 still FAILs, with a measured count, on a --full run whose head touches a listener"
    else
        _v=$(grep -oE '^\[gate-61\] [^:]+: [A-Z]+( [A-Z]+)?( \([a-z]+\))?' "${_o61}" | head -1 | sed 's/^[^:]*: //')
        _bad "gate-61 returned '${_v:-none}' over a listener doing HTTP + a write with no deferral — the provenance assertion below would prove nothing"
    fi

    # THE ASSERTION: a verdict derived from a diff must NAME that diff, in the
    # verdict, where the reader is.
    if grep -qE '^\[gate-61\][^:]*: FAIL .*(base|BASE).*origin/development' "${_o61}"; then
        _ok "gate-61's FAIL names the base it actually judged against"
    else
        _bad "gate-61 FAILED on a full-scope run WITHOUT naming the base it judged against — the run's own preamble says there is none, so the verdict's provenance is unreadable (.github#347 residual)"
    fi

    # The negative control for the note: a diff-scoped run already prints its
    # base in the preamble, so the note is noise there and must not appear.
    _l61s="${_tmp}/lwp-logs-scoped"; mkdir -p "${_l61s}"
    _o61s="${_tmp}/lwp-scoped.txt"
    ( cd "${_a61}" || exit 1
      HYDRA_GATE_LOG_DIR="${_l61s}" bash "${_bin}" \
          --base refs/remotes/origin/development > "${_o61s}" 2>&1 )
    if grep -qE '^\[gate-61\][^:]*: FAIL' "${_o61s}"; then
        if grep -qF 'full-scope run' "${_o61s}"; then
            _bad "gate-61 emitted its full-scope provenance note on a DIFF-SCOPED run, where the preamble already states the base — the note must be conditional, not unconditional"
        else
            _ok "gate-61 adds no provenance note on a diff-scoped run (the preamble already carries the base)"
        fi
    else
        _bad "gate-61 did not FAIL on the diff-scoped arm of the same tree — the negative control is invalid"
    fi

    # And the empty-diff case must STILL be `na`, not a verdict. #371's fix
    # must survive this change.
    _b61="${_tmp}/lwp-docs"
    _mk61 "${_b61}" no
    _l61b="${_tmp}/lwp-logs-docs"; mkdir -p "${_l61b}"
    _o61b="${_tmp}/lwp-docs.txt"
    ( cd "${_b61}" || exit 1
      HYDRA_GATE_LOG_DIR="${_l61b}" bash "${_bin}" --full > "${_o61b}" 2>&1 )
    if grep -qE '^\[gate-61\][^:]*: NOT APPLICABLE' "${_o61b}"; then
        _ok "the identical tree with a docs-only head is still NOT APPLICABLE — which is what proves the verdict above was diff-derived"
    else
        _v=$(grep -oE '^\[gate-61\] [^:]+: [A-Z]+( [A-Z]+)?( \([a-z]+\))?' "${_o61b}" | head -1 | sed 's/^[^:]*: //')
        _bad "gate-61 returned '${_v:-none}' on a docs-only head — #371's empty-scope reading has regressed"
    fi
fi

# ---------------------------------------------------------------------------
# gate-54 — INHERITED must be distinguishable from INTRODUCED, and both must
# still block.
# ---------------------------------------------------------------------------
_BANNED_SCHEMA='{
  "components": {
    "schemas": {
      "party": {
        "title": "Party",
        "type": "object",
        "x-openregister-relations": {
          "cases": { "target": "case", "cardinality": "many" }
        },
        "properties": { "name": { "type": "string" } }
      }
    }
  }
}'
_CLEAN_SCHEMA='{
  "components": {
    "schemas": {
      "party": {
        "title": "Party",
        "type": "object",
        "properties": { "name": { "type": "string" } }
      }
    }
  }
}'

_mk54() {  # <dir> <base-content> <head-content>
    local _d="$1" _base="$2" _head="$3"
    mkdir -p "${_d}/lib/Settings" "${_d}/appinfo"
    printf '<?xml version="1.0"?>\n<info>\n <id>rd</id>\n</info>\n' \
        > "${_d}/appinfo/info.xml"
    printf '%s\n' "${_base}" > "${_d}/lib/Settings/thing_register.json"
    (
        cd "${_d}" || exit 1
        git init -q .
        git symbolic-ref HEAD refs/heads/development
        git add -A
        _git_c commit -qm base
        git update-ref refs/remotes/origin/development HEAD
    ) >/dev/null 2>&1
    printf '%s\n' "${_head}" > "${_d}/lib/Settings/thing_register.json"
    (
        cd "${_d}" || exit 1
        git add -A
        _git_c commit -qm head
    ) >/dev/null 2>&1
}

_run54() {  # <dir> -> sets _o54
    local _d="$1"
    local _name _l
    # Declared and assigned separately: `local x=$(...)` takes `local`'s exit
    # status, not the substitution's, so a failing basename would be invisible
    # here (SC2155).
    _name="$(basename "${_d}")"
    _l="${_tmp}/rd-logs-${_name}"
    mkdir -p "${_l}"
    _o54="${_tmp}/rd-${_name}.txt"
    _log54="${_l}/hydra-gate-relation-dialect.log"
    ( cd "${_d}" || exit 1
      HYDRA_GATE_LOG_DIR="${_l}" bash "${_runner}" \
          --scope-to-diff --base refs/remotes/origin/development . \
          > "${_o54}" 2>&1 )
}

# ARM 1 — INHERITED. The banned dialect is byte-identical in base and head; the
# head's entire diff is one retitle.
_d54a="${_tmp}/rd-inherited"
_mk54 "${_d54a}" "${_BANNED_SCHEMA}" "${_BANNED_SCHEMA//\"Party\"/\"Counterparty\"}"
_run54 "${_d54a}"
if grep -qE '^\[gate-54\][^:]*: FAIL — [0-9]+ non-canonical' "${_o54}"; then
    _ok "gate-54 still BLOCKS on an inherited structural defect in a file the PR touched (the file-scoped design is kept)"
else
    _v=$(grep -oE '^\[gate-54\] [^:]+: [A-Z]+( [A-Z]+)?( \([a-z]+\))?' "${_o54}" | head -1 | sed 's/^[^:]*: //')
    _bad "gate-54 returned '${_v:-none}' — labelling a finding must not stop it blocking; that would be making the gate green by weakening it"
fi
if grep -qF 'INHERITED' "${_o54}" && grep -qF 'INHERITED' "${_log54}"; then
    _ok "the inherited finding is labelled INHERITED, in the verdict AND per-finding in the log"
else
    _bad "gate-54 reported a finding that is byte-identical at base and head without saying so — a reader cannot tell a defect they wrote from one they stood next to"
fi

# ARM 2 — INTRODUCED. Same gate, same file path, opposite direction. Without
# this arm, hardcoding the word INHERITED would satisfy arm 1.
_d54b="${_tmp}/rd-introduced"
_mk54 "${_d54b}" "${_CLEAN_SCHEMA}" "${_BANNED_SCHEMA}"
_run54 "${_d54b}"
if grep -qE '^\[gate-54\][^:]*: FAIL' "${_o54}"; then
    _ok "gate-54 FAILs when the head commit ADDS the banned dialect"
else
    _bad "gate-54 did not FAIL on a head commit that introduces the banned dialect"
fi
if grep -qF 'INTRODUCED' "${_log54}" && ! grep -qF 'INHERITED —' "${_log54}"; then
    _ok "the newly-added finding is labelled INTRODUCED and NOT inherited"
else
    _bad "gate-54 mislabelled a finding this change introduced: $(grep -oE '\[(INHERITED|INTRODUCED)[^]]*\]' "${_log54}" | head -2 | tr '\n' ' ')"
fi

# ARM 3 — the clean control. A canonical register must stay green, or "label
# everything" would pass arms 1 and 2.
_d54c="${_tmp}/rd-clean"
_mk54 "${_d54c}" "${_CLEAN_SCHEMA}" "${_CLEAN_SCHEMA//\"Party\"/\"Counterparty\"}"
_run54 "${_d54c}"
if grep -qE '^\[gate-54\][^:]*: PASS' "${_o54}"; then
    _ok "control: a canonical register with no banned dialect still PASSes"
else
    _v=$(grep -oE '^\[gate-54\] [^:]+: [A-Z]+( [A-Z]+)?( \([a-z]+\))?' "${_o54}" | head -1 | sed 's/^[^:]*: //')
    _bad "control FAILED: gate-54 returned '${_v:-none}' over a canonical register — the labelling has widened the gate"
fi

echo
if [ "${_failures}" -eq 0 ]; then
    echo "test_gate_diff_provenance.sh: ALL PASS"
    exit 0
fi
echo "test_gate_diff_provenance.sh: ${_failures} FAILURE(S)"
exit 1
