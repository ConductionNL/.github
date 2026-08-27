"""Execute the consolidated tool-family loops against stub tools.

`consolidate-tool-legs` turns six one-tool jobs into one six-tool job. The
danger is specific and quiet: `set -e` is ACTIVE in a GitHub `run:` block but
SUSPENDED inside a function invoked on the left of `||`, which is exactly how
`run_tool "$T" || RC=$?` calls it. A tool command without an explicit
`|| return $?` therefore falls through its case arm and the function returns 0
— a red tool reported green, inside the job whose entire purpose is catching
red tools.

So the loops are EXECUTED here, with stub tools whose exit codes are dictated
by a control file, and the assertions are about what the family reports.

THE SCRIPT UNDER TEST IS EXTRACTED FROM THE WORKFLOW, not copied into this
file. A copy would drift from the shipped text and this would then be a test of
a fiction that always passes.

Usage:
  python3 scripts/test-consolidated-tool-legs.py [.github/workflows/quality.yml]
  python3 scripts/test-consolidated-tool-legs.py --positive-control [workflow]

`--positive-control` removes the `|| return $?` guards — reintroducing the
exact bug described above — and requires this suite to go red.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

BREAK = "--positive-control" in sys.argv
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
WF = _args[0] if _args else ".github/workflows/quality.yml"

PHP_TOOLS = ["lint", "phpcs", "phpmd", "psalm", "phpstan", "phpmetrics"]
VUE_TOOLS = ["eslint", "stylelint"]


def step_run(job, name_contains):
    d = yaml.safe_load(open(WF))
    for s in d["jobs"][job]["steps"]:
        if name_contains in s.get("name", "") and "run" in s:
            src = s["run"]
            if BREAK:
                # Reintroduce the swallow: drop the explicit guards and let
                # `set -e` suspension hide a non-zero tool.
                src = src.replace(" || return $?", "")
            return src
    raise SystemExit(f"{job}: no run step matching {name_contains!r}")


def render(src, subs):
    """Resolve the ${{ ... }} expressions this harness needs."""
    for k, v in subs.items():
        src = src.replace("${{ " + k + " }}", v)
    left = re.findall(r"\$\{\{[^}]*\}\}", src)
    assert not left, f"unresolved expressions: {set(left)}"
    return src


def stub(d, name, body):
    p = os.path.join(d, "bin", name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(body)
    os.chmod(p, 0o755)


def run_php(failing=(), disabled=(), tool="all", missing_script=None):
    d = tempfile.mkdtemp()
    try:
        scripts = ", ".join(f'"{t}": "x"' for t in PHP_TOOLS
                            if t != missing_script)
        open(os.path.join(d, "composer.json"), "w").write(
            '{"scripts": {%s}}' % scripts)
        # `composer <script>` exits 1 for the scripts named in FAIL.
        stub(d, "composer", '#!/bin/bash\nfor f in $FAIL; do\n'
                            '  [ "$1" = "$f" ] && { echo "$1 FAILED"; exit 1; }\n'
                            'done\necho "$1 ok"\nexit 0\n')
        os.makedirs(os.path.join(d, "vendor", "bin"), exist_ok=True)
        open(os.path.join(d, "vendor", "bin", "phpcs"), "w").write(
            '#!/bin/bash\necho "PHP_CodeSniffer version 3.13.6"\n')
        os.chmod(os.path.join(d, "vendor", "bin", "phpcs"), 0o755)

        subs = {"matrix.tool": tool, "job.status": "failure"}
        for t in ("phpcs", "phpmd", "psalm", "phpstan", "phpmetrics"):
            subs[f"inputs.enable-{t}"] = "false" if t in disabled else "true"
        src = render(step_run("php-quality", "Run "), subs)

        env = dict(os.environ)
        env["PATH"] = os.path.join(d, "bin") + os.pathsep + env["PATH"]
        env["FAIL"] = " ".join(failing)
        r = subprocess.run(["bash", "-eo", "pipefail", "-c", src],
                           cwd=d, env=env, capture_output=True, text=True)
        results = {}
        qd = os.path.join(d, "quality-results")
        if os.path.isdir(qd):
            for f in os.listdir(qd):
                results[f[:-4]] = open(os.path.join(qd, f)).read().strip()
        return r.returncode, results, r.stdout + r.stderr
    finally:
        shutil.rmtree(d, ignore_errors=True)


def run_vue(failing=(), disabled=()):
    d = tempfile.mkdtemp()
    try:
        stub(d, "npm", '#!/bin/bash\n[ "$1" = "run" ] || exit 0\n'
                       'for f in $FAIL; do [ "$2" = "$f" ] && exit 1; done\n'
                       'echo "$2 ok"\nexit 0\n')
        subs = {"matrix.tool": "all", "job.status": "failure",
                "inputs.enable-eslint": "false" if "eslint" in disabled else "true",
                "inputs.enable-stylelint": "false" if "stylelint" in disabled else "true",
                "inputs.frontend-path": "."}
        src = render(step_run("vue-quality", "Run "), subs)
        env = dict(os.environ)
        env["PATH"] = os.path.join(d, "bin") + os.pathsep + env["PATH"]
        # npm script names, not tool names: eslint -> lint, stylelint -> stylelint
        env["FAIL"] = " ".join("lint" if f == "eslint" else f for f in failing)
        r = subprocess.run(["bash", "-eo", "pipefail", "-c", src],
                           cwd=d, env=env, capture_output=True, text=True)
        results = {}
        qd = os.path.join(d, "quality-results")
        if os.path.isdir(qd):
            for f in os.listdir(qd):
                results[f[:-4]] = open(os.path.join(qd, f)).read().strip()
        return r.returncode, results, r.stdout + r.stderr
    finally:
        shutil.rmtree(d, ignore_errors=True)


def run_security(install_fails=False, audit_fails=False, npm_ci_fails=False):
    d = tempfile.mkdtemp()
    try:
        stub(d, "composer",
             '#!/bin/bash\n'
             'case "$1" in\n'
             '  install) [ "$INSTALL_FAILS" = 1 ] && { echo "install failed"; exit 1; };;\n'
             '  audit)   [ "$AUDIT_FAILS" = 1 ] && { echo "vuln found"; exit 1; };;\n'
             'esac\necho "composer $1 ok"\nexit 0\n')
        stub(d, "npm",
             '#!/bin/bash\n'
             '[ "$1" = "ci" ] && { [ "$NPM_CI_FAILS" = 1 ] && exit 1; echo "npm ci ok"; exit 0; }\n'
             'echo "npm $1 ok"\nexit 0\n')
        src = render(step_run("security", "audit"),
                     {"matrix.ecosystem": "all", "job.status": "failure",
                      "inputs.enable-php": "true", "inputs.enable-npm": "true"})
        env = dict(os.environ)
        env["PATH"] = os.path.join(d, "bin") + os.pathsep + env["PATH"]
        env["FRONTEND_PATH"] = "."
        env["INSTALL_FAILS"] = "1" if install_fails else "0"
        env["AUDIT_FAILS"] = "1" if audit_fails else "0"
        env["NPM_CI_FAILS"] = "1" if npm_ci_fails else "0"
        r = subprocess.run(["bash", "-eo", "pipefail", "-c", src],
                           cwd=d, env=env, capture_output=True, text=True)
        results = {}
        qd = os.path.join(d, "quality-results")
        if os.path.isdir(qd):
            for f in os.listdir(qd):
                results[f[:-4]] = open(os.path.join(qd, f)).read().strip()
        return r.returncode, results, r.stdout + r.stderr
    finally:
        shutil.rmtree(d, ignore_errors=True)


ok = []


def check(label, cond, detail=""):
    ok.append(cond)
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond and detail:
        print("        " + detail.replace("\n", "\n        ")[:900])


print("── PHP Quality, consolidated ─────────────────────────────────────")
rc, res, log = run_php()
check("all six tools green -> job exits 0", rc == 0, log)
check("all six record success",
      all(res.get(t) == "success" for t in PHP_TOOLS), str(res))

for bad in ("psalm", "phpstan", "lint", "phpmd", "phpmetrics"):
    rc, res, log = run_php(failing=[bad])
    check(f"{bad} red -> job FAILS (not swallowed)", rc != 0, log)
    check(f"{bad} red -> only {bad} records failure",
          res.get(bad) == "failure"
          and all(res.get(t) == "success" for t in PHP_TOOLS if t != bad),
          str(res))

rc, res, log = run_php(failing=["psalm", "phpmd"])
check("two red -> job fails and BOTH record failure",
      rc != 0 and res.get("psalm") == "failure" and res.get("phpmd") == "failure",
      str(res))

rc, res, log = run_php(disabled=["phpmd"])
check("a disabled tool does not fail the family", rc == 0, log)
check("a disabled tool still records a result", res.get("phpmd") == "success", str(res))

rc, res, log = run_php(failing=["psalm"], tool="psalm")
check("SPLIT mode still works (one tool, red)", rc != 0 and res.get("psalm") == "failure", str(res))
rc, res, log = run_php(tool="psalm")
check("SPLIT mode writes only its own tool's file",
      list(res) == ["psalm"] and res["psalm"] == "success", str(res))

print("── A failure in a NON-LAST command of an arm ─────────────────────")
# THE CASE THAT MATTERS. Bash returns a function's LAST command's status, so a
# guard on the last command of a case arm is belt-and-braces. A guard on any
# EARLIER command is load-bearing: without it, execution falls through to the
# next command, and that command's success becomes the family's verdict.
rc, res, log = run_php(missing_script="psalm")
check("composer.json missing the psalm script -> family FAILS", rc != 0, log)
check("...and psalm records failure, not success",
      res.get("psalm") == "failure", str(res))

print("── Security, consolidated ────────────────────────────────────────")
rc, res, log = run_security()
check("both ecosystems clean -> exits 0",
      rc == 0 and res.get("composer") == "success" and res.get("npm") == "success",
      str(res) + log)
rc, res, log = run_security(audit_fails=True)
check("composer audit finds a vuln -> family FAILS",
      rc != 0 and res.get("composer") == "failure", str(res) + log)
rc, res, log = run_security(install_fails=True)
check("composer INSTALL fails -> family FAILS (audit must not mask it)",
      rc != 0 and res.get("composer") == "failure", str(res) + log)
rc, res, log = run_security(npm_ci_fails=True)
check("npm ci fails -> family FAILS (audit must not mask it)",
      rc != 0 and res.get("npm") == "failure", str(res) + log)

print("── Vue Quality, consolidated ─────────────────────────────────────")
rc, res, log = run_vue()
check("both green -> exits 0 and records success",
      rc == 0 and all(res.get(t) == "success" for t in VUE_TOOLS), str(res))
rc, res, log = run_vue(failing=["eslint"])
check("eslint red -> job FAILS", rc != 0, log)
check("eslint red -> stylelint still ran and recorded",
      res.get("eslint") == "failure" and res.get("stylelint") == "success", str(res))

print()
passed, total = sum(ok), len(ok)
if BREAK:
    if passed == total:
        print("::error::POSITIVE CONTROL DID NOT FIRE — the `|| return $?` guards "
              "were removed and every case still passed. This suite is not "
              "exercising the shipped script.")
        sys.exit(1)
    print(f"OK — the control fires: {total - passed} case(s) failed once the "
          f"guards were removed, so a clean pass of this suite is a verdict.")
    sys.exit(0)

print(f"{passed}/{total} passed")
if passed != total:
    print("::error::A consolidated tool family does not report correctly. A "
          "swallowed failure here is a red tool rendered green.")
sys.exit(0 if passed == total else 1)
