#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# gate_fixture_support.sh — shared helpers for the repo-shaped gate suites.
#
# NOTE ON THE FILENAME: this file deliberately does NOT start with `test_`.
# tests/run-helper-suites.sh DISCOVERS `scripts/lib/test_*` and executes each as
# a suite; a shared library picked up by that glob would be run as a test, find
# no assertions, and exit 0 — an empty green, which is the exact failure mode
# this package keeps getting bitten by.
#
# WHY REAL GIT REPOS
# ------------------
# The existing fixture families are plain directories tracked inside the
# `.github` repo. That works for unscoped runs, because the gates enumerate
# through `git ls-files`, which resolves against `.github`'s own index. It
# cannot express a DIFF: there is no base ref and no history to diff against.
#
# That is precisely why no existing fixture could have caught gate-61, whose
# defect is a SCOPE bug — the checker is correct and the wrapper hands it the
# wrong scope. It is also why none of them can catch the disk-vs-committed
# divergence class (gate-16 reads `@spec` from disk while deriving its changed
# method set from committed history, so an UNCOMMITTED plant yields a false
# PASS and can manufacture a false "this gate is blind").
#
# So these helpers materialise a fixture as a real repository with a real base
# ref and a real HEAD, and every plant is COMMITTED before it is measured.

# gf_build_repo <dest> <src-tree> <base-spec> <head-spec>
#
#   base-spec / head-spec are newline-free shell snippets executed inside the
#   repo, letting a caller shape each commit. `origin/development` is created as
#   a genuine remote-tracking ref (refs/remotes/origin/development) so the
#   wrapper's own auto-detection chain resolves it exactly as it does in CI.
#
# `git init -b` is NOT used: the git on this host predates it and fails with
# "unknown switch `b'", leaving an uninitialised directory that every later
# command reports as "not a git repository" — which reads like a fixture bug
# rather than a tooling one.
gf_build_repo() {
    local _dest="$1" _src="$2"
    rm -rf "${_dest}"; mkdir -p "${_dest}"
    cp -r "${_src}/." "${_dest}/"
    (
        cd "${_dest}" || exit 1
        git init -q . || exit 1
        git symbolic-ref HEAD refs/heads/development
        git config user.email fixture@example.invalid
        git config user.name "Gate Fixture"
        git config commit.gpgsign false
    )
}

# gf_commit_all <repo> <message>
# `git add -f` because a fixture may deliberately ship a .gitignore that hides
# its own plant (the gate-4 shape) — and also because these trees are copied
# out of a repo that ignores build artefacts. NEVER `git add -A` at the caller
# level: these checkouts are shared between sessions.
gf_commit_all() {
    local _repo="$1" _msg="$2"
    ( cd "${_repo}" && git add -f . >/dev/null 2>&1 && git commit -qm "${_msg}" )
}

# gf_commit_paths <repo> <message> <path...>
gf_commit_paths() {
    local _repo="$1" _msg="$2"; shift 2
    ( cd "${_repo}" && git add -f "$@" >/dev/null 2>&1 && git commit -qm "${_msg}" )
}

# gf_mark_base <repo>  — point origin/development at the current HEAD.
gf_mark_base() {
    ( cd "$1" && git update-ref refs/remotes/origin/development "$(git rev-parse HEAD)" )
}

# gf_run_wrapper <repo> <logdir> [args...] -> stdout+stderr of bin/hydra-gates
# Drives the REAL distributable entry point, not the runner underneath it. The
# gate-61 defect lives in bin/hydra-gates (it does not forward `--base` on
# `--full`), so a suite that called run-hydra-gates.sh directly would miss it.
gf_run_wrapper() {
    local _repo="$1" _logdir="$2"; shift 2
    mkdir -p "${_logdir}"
    HYDRA_GATE_LOG_DIR="${_logdir}" HYDRA_OR_GATE_BLOCK_AFTER_EPOCH=0 \
        bash "${GF_PKG_ROOT}/bin/hydra-gates" "$@" --app-dir "${_repo}" 2>&1
}

# gf_verdict <output> <gate-n>
# A gate may print advisory lines that carry its own `[gate-N] ` prefix before
# it prints its verdict — gate-61's provenance NOTE is the first. `head -1` used
# to return whichever came first, so a NOTE silently DISPLACED the verdict and
# every assertion here read "no FAIL" while the gate was failing correctly.
#
# MATCH THE VERDICT BY ITS SHAPE, NOT BY EXCLUDING THE ADVISORIES SOMEONE
# REMEMBERED TO LIST (.github#401)
# ----------------------------------------------------------------------
# The `NOTE|WARN|INFO:` denylist below is exact and was still one advisory
# short. gate-48 printed
#
#   [gate-48] no CSRF signal was ADDED by this diff, and none was needed: ...
#
# BEFORE its verdict, carrying none of those three tags, so this function
# returned the advisory — and the acceptance matrix's own `_verdict`, which
# filters nothing at all, did the same. The reader's message in that case is
# "gate-48 emitted NO verdict line at all", i.e. a gate defect that does not
# exist. Any "first line wins" parser is one advisory away from reporting
# silence, and a denylist can only ever be repaired one entry at a time, after
# the fact.
#
# So: match the four shapes `_pass` / `_fail` / `_skip` can actually emit —
# `PASS`, `FAIL — …`, `NOT APPLICABLE — …`, `SKIPPED (na|structural|wiring) — …`
# — all of which are `[gate-N] <name>: <VERDICT>`. An advisory cannot forge
# that shape without literally claiming a verdict.
#
# The denylist survives as a FALLBACK, and only as one. If the emitters ever
# grow a fifth verdict word this keeps returning what it returns today rather
# than returning nothing — because "no verdict line" is itself a load-bearing
# assertion in the suites, and a parser that silently starts producing it
# would manufacture exactly the false gate defect this change removes.
gf_verdict() {
    local _v
    # WARNING joined the set with .github#477 — kept in step with `_verdict`
    # in test_gate_acceptance_matrix.sh.
    _v=$(printf '%s' "$1" | grep -E "^\[gate-$2\] [^:]+: (PASS|FAIL|WARNING|NOT APPLICABLE|SKIPPED)\b" | head -1)
    if [ -n "${_v}" ]; then
        printf '%s' "${_v}"
        return 0
    fi
    printf '%s' "$1" | grep -E "^\[gate-$2\] " | grep -vE "^\[gate-[0-9]+\] (NOTE|WARN|INFO):" | head -1
}
