#!/usr/bin/env python3
"""Exercise quality-config/assert-lockfile-matches-install.js against built trees.

Each case writes a package.json, a package-lock.json and an installed
node_modules tree into a temporary app directory, runs the guard there and
checks its exit code and the line it prints.

Usage: test-assert-lockfile.py [path-to-guard.js]
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(
    HERE, "..", "assert-lockfile-matches-install.js"
)


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


def build(root, deps, dev_deps, lock_packages, installed):
    """installed maps an install path under node_modules/ to its version."""
    if deps is not None:
        write(os.path.join(root, "package.json"),
              {"name": "app", "dependencies": deps, "devDependencies": dev_deps})
    if lock_packages is not None:
        write(os.path.join(root, "package-lock.json"),
              {"lockfileVersion": 3, "packages": {"": {"name": "app"}, **lock_packages}})
    if installed is not None:
        os.makedirs(os.path.join(root, "node_modules"), exist_ok=True)
        for entry, version in installed.items():
            write(os.path.join(root, "node_modules", entry, "package.json"),
                  {"name": entry.split("node_modules/")[-1], "version": version})


LOCK = {
    "node_modules/vue-router": {"version": "4.6.4"},
    "node_modules/eslint": {"version": "10.10.0", "dev": True},
}
DEPS = {"vue-router": "^4.6.4"}
DEV = {"eslint": "^10.10.0"}

CASES = [
    # name, (deps, dev, lock, installed), want rc, text the output must contain
    ("no lockfile is skipped", (DEPS, DEV, None, {}), 0, "skipped"),
    ("no node_modules is skipped", (DEPS, DEV, LOCK, None), 0, "nothing built yet"),
    ("matching tree passes",
     (DEPS, DEV, LOCK, {"vue-router": "4.6.4", "eslint": "10.10.0"}), 0, "OK"),
    ("runtime version drift fails",
     (DEPS, DEV, LOCK, {"vue-router": "3.6.5", "eslint": "10.10.0"}), 1, "vue-router"),
    ("missing runtime dependency fails",
     (DEPS, DEV, LOCK, {"eslint": "10.10.0"}), 1, "(absent)"),
    ("dev drift is reported, not fatal",
     (DEPS, DEV, LOCK, {"vue-router": "4.6.4", "eslint": "9.0.0"}), 0, "dev-dependency drift"),
    ("absent optional dependency is not drift",
     ({**DEPS, "fsevents": "^2.3.3"}, DEV, {**LOCK, "node_modules/fsevents": {"version": "2.3.3", "optional": True}},
      {"vue-router": "4.6.4", "eslint": "10.10.0"}), 0, "OK"),
    ("nested copy with another version is not drift",
     (DEPS, DEV, {**LOCK, "node_modules/a/node_modules/vue-router": {"version": "3.6.5"}},
      {"vue-router": "4.6.4", "eslint": "10.10.0",
       "a/node_modules/vue-router": "3.0.0"}), 0, "OK"),
]


def main():
    failed = 0
    for name, (deps, dev, lock, installed), want_rc, want_text in CASES:
        with tempfile.TemporaryDirectory() as root:
            build(root, deps, dev, lock, installed)
            proc = subprocess.run(["node", GUARD], cwd=root, capture_output=True, text=True)
            out = proc.stdout + proc.stderr
            ok = proc.returncode == want_rc and want_text in out
            # A clean tree reports no drift line at all, not even a dev one.
            if want_text == "OK":
                ok = ok and "drift" not in out
            failed += not ok
            print(f"  {'ok  ' if ok else 'FAIL'}  {name:48} rc={proc.returncode} (want {want_rc})")
    print(f"{len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
