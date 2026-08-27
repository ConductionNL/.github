"""Execute the `changes` job's real shell script against real git history.

The changed-path filter decides whether PHPUnit and Playwright run at all, so a
bug in it does not fail — it silently removes the test tier and renders as a
green run over untested code. That is the single most dangerous shape in this
workflow, so the filter is executed here against real git repositories rather
than reasoned about.

THE SCRIPT UNDER TEST IS EXTRACTED FROM THE WORKFLOW, not copied into this
file. A copy would drift from the shipped text and this would then be a test of
a fiction that always passes.

Usage:
  python3 scripts/test-changed-path-filter.py [.github/workflows/quality.yml]
  python3 scripts/test-changed-path-filter.py --positive-control [workflow]

`--positive-control` breaks the filter's fail-safe on purpose and requires this
suite to go red. A suite that cannot fail is not evidence.
"""
import os
import shutil
import subprocess
import sys
import tempfile

import yaml

ZERO = "0" * 40
BREAK = "--positive-control" in sys.argv
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
WF = _args[0] if _args else ".github/workflows/quality.yml"


def script():
    d = yaml.safe_load(open(WF))
    for s in d["jobs"]["changes"]["steps"]:
        if s.get("id") == "decide":
            src = s["run"]
            if BREAK:
                # Sabotage the fail-safe: make the "filtering is off" path emit
                # `false` instead of `true`. The "filtering disabled" case below
                # must then fail. If it does not, this suite is not reading the
                # script it claims to test.
                broken = src.replace(
                    'run_everything "path filtering is not enabled',
                    'emit false "SABOTAGED — path filtering is not enabled')
                assert broken != src, "positive control could not find its anchor"
                return broken
            return src
    raise SystemExit("decide step not found")


def git(*a, cwd):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True,
                          check=True).stdout.strip()


def make_repo(d):
    git("init", "-q", "-b", "main", cwd=d)
    git("config", "user.email", "t@t", cwd=d)
    git("config", "user.name", "t", cwd=d)
    return d


def commit(d, files, msg):
    for path, body in files.items():
        full = os.path.join(d, path)
        os.makedirs(os.path.dirname(full), exist_ok=True) if "/" in path else None
        open(full, "w").write(body)
    git("add", "-A", cwd=d)
    git("commit", "-qm", msg, cwd=d)
    return git("rev-parse", "HEAD", cwd=d)


def run_case(name, files_before, files_after, event, filter_on="true",
             globs="lib/** src/** tests/** appinfo/** composer.json composer.lock package.json package-lock.json .github/workflows/**",
             expect=None):
    d = tempfile.mkdtemp()
    try:
        make_repo(d)
        base = commit(d, files_before, "base")
        head = commit(d, files_after, "head") if files_after else base
        out_f = os.path.join(d, "gh_out")
        sum_f = os.path.join(d, "gh_sum")
        open(out_f, "w").close()
        open(sum_f, "w").close()
        env = dict(os.environ)
        env.update({
            "GITHUB_OUTPUT": out_f, "GITHUB_STEP_SUMMARY": sum_f,
            "FILTER_ON": filter_on, "GLOBS": globs, "EVENT": event,
            "BASE_SHA": base if event == "pull_request" else "",
            "HEAD_SHA": head,
            "BEFORE": base if event == "push" else "",
        })
        r = subprocess.run(["bash", "-c", script()], cwd=d, env=env,
                           capture_output=True, text=True)
        outs = dict(l.split("=", 1) for l in open(out_f).read().splitlines() if "=" in l)
        got = outs.get("code")
        ok = (got == expect)
        print(f"  {'PASS' if ok else 'FAIL'}  {name:52} code={got!r} (want {expect!r}) rc={r.returncode}")
        if not ok:
            print("        stdout:", r.stdout[-600:])
            print("        stderr:", r.stderr[-400:])
        return ok
    finally:
        shutil.rmtree(d, ignore_errors=True)


def special(name, event, before, filter_on, expect):
    """Cases that need a hand-built env (branch creation, unknown event)."""
    d = tempfile.mkdtemp()
    try:
        make_repo(d)
        head = commit(d, {"lib/A.php": "<?php\n"}, "only")
        out_f = os.path.join(d, "o"); sum_f = os.path.join(d, "s")
        open(out_f, "w").close(); open(sum_f, "w").close()
        env = dict(os.environ)
        env.update({"GITHUB_OUTPUT": out_f, "GITHUB_STEP_SUMMARY": sum_f,
                    "FILTER_ON": filter_on, "GLOBS": "lib/**", "EVENT": event,
                    "BASE_SHA": "", "HEAD_SHA": head, "BEFORE": before})
        subprocess.run(["bash", "-c", script()], cwd=d, env=env,
                       capture_output=True, text=True)
        outs = dict(l.split("=", 1) for l in open(out_f).read().splitlines() if "=" in l)
        got = outs.get("code")
        ok = got == expect
        print(f"  {'PASS' if ok else 'FAIL'}  {name:52} code={got!r} (want {expect!r})")
        return ok
    finally:
        shutil.rmtree(d, ignore_errors=True)


PHP = "<?php\nclass A {}\n"
results = []
print("── SHOULD SKIP (the whole point) ─────────────────────────────────")
results.append(run_case("l10n-only change", {"l10n/en.json": "{}"},
                        {"l10n/en.json": '{"a":"b"}'}, "pull_request", expect="false"))
results.append(run_case("docs-only change", {"docs/x.md": "a"},
                        {"docs/x.md": "b"}, "push", expect="false"))
results.append(run_case("openspec-only change", {"openspec/s.md": "a"},
                        {"openspec/s.md": "b"}, "pull_request", expect="false"))

print("── SHOULD RUN (a missed one is a lost verdict) ───────────────────")
results.append(run_case("lib/ php change", {"lib/A.php": PHP},
                        {"lib/A.php": PHP + "// x\n"}, "pull_request", expect="true"))
results.append(run_case("src/ vue change", {"src/A.vue": "<template/>"},
                        {"src/A.vue": "<template><b/></template>"}, "push", expect="true"))
results.append(run_case("composer.lock change", {"composer.lock": "{}"},
                        {"composer.lock": '{"x":1}'}, "pull_request", expect="true"))
results.append(run_case("tests/ change", {"tests/T.php": PHP},
                        {"tests/T.php": PHP + "//\n"}, "pull_request", expect="true"))
results.append(run_case("mixed docs + php", {"docs/a.md": "a", "lib/A.php": PHP},
                        {"docs/a.md": "b", "lib/A.php": PHP + "//\n"},
                        "pull_request", expect="true"))

print("── FAIL-SAFE: uncertainty must resolve to RUN ────────────────────")
results.append(run_case("filtering disabled", {"docs/a.md": "a"},
                        {"docs/a.md": "b"}, "pull_request",
                        filter_on="false", expect="true"))
results.append(special("push that created the branch (BEFORE=zeros)",
                       "push", ZERO, "true", "true"))
results.append(special("workflow_dispatch (no diff defined)",
                       "workflow_dispatch", "", "true", "true"))
results.append(special("schedule (no diff defined)", "schedule", "", "true", "true"))

print("── THE TWO RULES MUST AGREE ──────────────────────────────────────")
results.append(run_case("php file OUTSIDE the globs -> distrust filter",
                        {"weird/A.php": PHP}, {"weird/A.php": PHP + "//\n"},
                        "pull_request", globs="lib/** src/**", expect="true"))
results.append(run_case("vue file OUTSIDE the globs -> distrust filter",
                        {"frontend/A.vue": "<template/>"},
                        {"frontend/A.vue": "<template><b/></template>"},
                        "pull_request", globs="lib/**", expect="true"))

print()
passed, total = sum(results), len(results)
if BREAK:
    if passed == total:
        print("::error::POSITIVE CONTROL DID NOT FIRE — the filter's fail-safe "
              "was sabotaged and every case still passed. This suite is not "
              "exercising the shipped script.")
        sys.exit(1)
    print(f"OK — the control fires: {total - passed} case(s) failed with a "
          f"sabotaged fail-safe, so a clean pass of this suite is a verdict.")
    sys.exit(0)

print(f"{passed}/{total} passed")
if passed != total:
    print("::error::The changed-path filter is not behaving as specified. A "
          "wrong answer here deletes the test tier silently.")
sys.exit(0 if passed == total else 1)
