#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Self-test for check_forbidden_patterns.py (gate-2).

gate-2 failed in BOTH directions at once — the #184 shape. Each assertion below
names the measured behaviour it pins.

Run: python3 scripts/lib/test_check_forbidden_patterns.py   (exit 0 = green)
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from check_forbidden_patterns import scan_file  # noqa: E402

_FAILED: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"PASS — {name}")
    else:
        print(f"FAIL — {name}{(': ' + detail) if detail else ''}")
        _FAILED.append(name)


def run(body: str) -> list[str]:
    src = "<?php\nclass P {\n" + body + "\n}\n"
    fd, path = tempfile.mkstemp(suffix=".php")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(src)
        return scan_file(path)
    finally:
        os.unlink(path)


# --- baseline: the shapes the old grep already caught ----------------------
for name in ("var_dump", "print_r", "error_log", "dd", "dump"):
    f = run(f"    public function a(): void {{ {name}($x); }}")
    check(f"{name}( is reported", len(f) == 1, repr(f))

# --- FALSE NEGATIVES the old grep could not see ----------------------------
f = run("    public function a(): void { var_dump ($x); }")
check("var_dump WITH A SPACE before ( is reported", len(f) == 1, repr(f))

f = run("    public function a(): void { die; }")
check("bare `die;` (language construct) is reported", len(f) == 1, repr(f))

f = run("    public function a(): void { die('gone'); }")
check("die('x') is reported", len(f) == 1, repr(f))

f = run("    public function a(): void { exit; }")
check("bare `exit;` is reported", len(f) == 1, repr(f))

f = run("    public function a(): void { exit(1); }")
check("exit(1) is reported", len(f) == 1, repr(f))

# --- FALSE POSITIVES the old grep produced ---------------------------------
f = run("    // TODO: never use var_dump( here\n    public function a(): void { echo 1; }")
check("a COMMENT warning against var_dump( is NOT reported", f == [], repr(f))

f = run('    public function a(): void { $sql = "select dd(x)"; }')
check("a STRING LITERAL containing dd( is NOT reported", f == [], repr(f))

f = run("    /**\n     * Do not call die() here.\n     */\n    public function a(): void { echo 1; }")
check("a docblock mentioning die() is NOT reported", f == [], repr(f))

# --- ANTI-WIDENING: `: never` is a TYPE, and it exempts --------------------
f = run("    public function a(): never { exit; }")
check("exit inside a `: never` function is NOT reported", f == [], repr(f))

f = run("    public function a(): never { die('bye'); }")
check("die inside a `: never` function is NOT reported", f == [], repr(f))

f = run("    public function a(): void { exit; }\n    public function b(): never { exit; }")
check(
    "the `: never` exemption is per-function, not per-file",
    len(f) == 1,
    repr(f),
)

# --- ANTI-WIDENING: identifiers that merely contain the word ---------------
f = run("    public function a(): void { $exit = 1; return $exit; }")
check("a variable named $exit is NOT reported", f == [], repr(f))

f = run("    public function a(): void { $this->exit(); }")
check("a METHOD call ->exit() is NOT reported", f == [], repr(f))

f = run("    public function a(): void { $exit_code = 1; }")
check("an identifier `exit_code` is NOT reported", f == [], repr(f))

# --- A DECLARATION IS NOT A CALL (2026-08-12) ------------------------------
# `die`/`exit` are SEMI-RESERVED in PHP: illegal as a free function name, legal
# as a method name. The construct pattern saw the parameter list's `(` and
# reported the method HEADER as a call. Both arms below, so a fix that removes
# the false positive by dropping the construct rule fails the second one.
f = run("    private function exit(): void { $this->exitCode = 1; }")
check("a method DECLARATION `function exit()` is NOT reported", f == [], repr(f))

f = run("    private function die(): void { $this->done = true; }")
check("a method DECLARATION `function die()` is NOT reported", f == [], repr(f))

f = run("    private function &exit(): array { return []; }")
check("a by-reference declaration `function &exit()` is NOT reported", f == [], repr(f))

f = run("    abstract protected function exit(): void;")
check("a BODILESS declaration `function exit();` is NOT reported", f == [], repr(f))

f = run("    public function a(): void { self::exit(); }")
check("a STATIC call ::exit() is NOT reported", f == [], repr(f))

# The true-positive half. Exempting the header must not exempt the body, nor a
# construct in a method whose NAME merely starts with the word.
f = run("    private function exit(): void { exit; }")
check(
    "`exit;` INSIDE a method named exit() is STILL reported (header only is exempt)",
    len(f) == 1,
    repr(f),
)

f = run("    public function exitEarly(): void { exit(0); }")
check(
    "`exit(0)` in a method named exitEarly() is STILL reported",
    len(f) == 1,
    repr(f),
)

# --- MUTATION CHECK: assert the guards exist before trusting the negatives --
_SRC = open(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "check_forbidden_patterns.py"
    )
).read()
check("the `: never` exemption is in the source", "_never_spans" in _SRC)
check("string blanking is requested", "blank_strings=True" in _SRC)
check("die/exit are matched as constructs", "_CONSTRUCT_RX" in _SRC)
check("the declaration discriminator is in the source", "_declared_name_offsets" in _SRC)

print()
if _FAILED:
    print(f"FAILED: {len(_FAILED)} — {_FAILED}")
    sys.exit(1)
print("ALL check_forbidden_patterns assertions passed")
