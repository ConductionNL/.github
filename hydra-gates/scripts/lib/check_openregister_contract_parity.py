#!/usr/bin/env python3
"""Gate 67 — the published OpenRegister contract has exactly one definition.

ADR-084 says OpenRegister publishes the surface it is consumed through, so that
sixteen apps stop hand-rolling doubles of a class they do not own. Measured
2026-08-14, TEN of them already had one, declaring between 0 and 13 methods
against a real class of 88.

That promise needs the interface in two places, for two different reasons:

  lib/Contract/                              openregister, at RUNTIME.
      `class ObjectService implements ObjectServiceInterface` is resolved when
      the class is autoloaded. If the interface were only in a require-dev
      package it would be ABSENT from a production install (`composer install
      --no-dev`) and every route would fatal -- the exact failure ADR-083
      rule 2 exists to prevent.

  hydra-gates/contracts/                     leaf apps, under PHPUnit.
      A leaf app cannot load a class from another Nextcloud app, which is the
      whole reason the contract exists. hydra-gates is already require-dev in
      every app, so shipping the interface there puts it in each consumer's
      vendor/ where a test double can implement it.

Two copies is a drift risk, and "we will keep them in step" is not a mechanism.
This gate IS the mechanism: the copies must be byte-identical, or the build is
red. One definition, enforced rather than promised.

Finding the shipped copy is not as simple as it looks. The Hydra Gates job
fetches this runner from `.github@main` and never runs `composer install`, so in
CI there is no `vendor/` to read -- the first version of this gate looked only
there and consequently reported NOT APPLICABLE on every run. Three locations are
tried, in this order:

    vendor/conduction/hydra-gates/...   the consumer's own install, so an app
                                        pinning an older hydra-gates is judged
                                        against the version it actually ships
    hydra-gates/contracts/              inside the .github repo itself
    <alongside this script>             the copy that travels with the runner

A repo with no lib/Contract/ does not own the contract and is skipped; it is not
judged, so it is not reported as a pass.

Exit codes
    0  the copies agree
    1  they differ -- see the FAIL lines
    3  no lib/Contract/ -- this repo does not own the contract
    4  lib/Contract/ exists but no shipped copy was found in any of the three
       locations. NOT a pass: nothing was verified.

Every run ends by printing `checked N file(s)`. A run that stops before that
line CRASHED, and the runner treats a missing line as a failure rather than as
a clean tree -- a dead checker otherwise reports as a pass.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Where each copy lives, relative to the repository root.
CANONICAL_DIR = Path("lib") / "Contract"
SHIPPED_DIR = Path("vendor") / "conduction" / "hydra-gates" / "hydra-gates" / "contracts"

# The same directory, seen from inside the .github repo itself, where there is
# no vendor/ because the package IS this repo.
SELF_DIR = Path("hydra-gates") / "contracts"

# And the copy that travels WITH THIS SCRIPT.
#
# This is the one that actually works in CI. The gates runner is fetched from
# `.github@main` rather than installed from composer, so the Hydra Gates job has
# no `vendor/` at all — the first version of this gate looked only in vendor/ and
# therefore reported NOT APPLICABLE on every run, including the run whose whole
# purpose was to bump the lock to a version that ships the contracts. A gate that
# can only skip protects nothing.
#
# scripts/lib/<this file> -> scripts/lib -> scripts -> hydra-gates -> contracts/
RUNNER_DIR = Path(__file__).resolve().parent.parent.parent / "contracts"


def _php_files(directory: Path) -> dict[str, Path]:
    """Map basename -> path for every .php file directly in `directory`."""
    if not directory.is_dir():
        return {}
    return {p.name: p for p in sorted(directory.glob("*.php"))}


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:  # unreadable is a finding, not a crash
        return f"<<unreadable: {exc}>>".encode()


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()

    canonical = _php_files(root / CANONICAL_DIR)
    if not canonical:
        print(
            "SKIP no lib/Contract/ in this repository — it does not own the "
            "OpenRegister contract, so there is nothing to keep in step."
        )
        print("checked 0 file(s)")
        return 3

    # Order matters. The consumer's own vendor/ wins when it exists, so an app
    # that pins an older hydra-gates is judged against the version it actually
    # installs. Only then fall back to the copy shipped with this script.
    for candidate in (root / SHIPPED_DIR, root / SELF_DIR, RUNNER_DIR):
        if candidate.is_dir() and any(candidate.glob("*.php")):
            shipped_dir = candidate
            break
    else:
        shipped_dir = root / SHIPPED_DIR
    shipped = _php_files(shipped_dir)
    if not shipped:
        print(
            "SKIP lib/Contract/ exists but no shipped copy was found at "
            f"{SHIPPED_DIR}, {SELF_DIR} or alongside this checker "
            f"({RUNNER_DIR}). Nothing was compared, so this is NOT a pass."
        )
        print(f"checked {len(canonical)} file(s)")
        return 4

    findings = 0
    checked = 0

    for name in sorted(set(canonical) | set(shipped)):
        checked += 1
        left = canonical.get(name)
        right = shipped.get(name)

        if left is None:
            findings += 1
            # Report the path the reader can act on, not the absolute one the
            # runner happened to resolve.
            try:
                where = (shipped_dir / name).relative_to(root)
            except ValueError:
                where = shipped_dir / name
            print(
                f"FAIL {where}: shipped in hydra-gates but absent "
                f"from {CANONICAL_DIR}/. Consumers would compile against an "
                "interface OpenRegister does not implement."
            )
            continue

        if right is None:
            findings += 1
            print(
                f"FAIL {CANONICAL_DIR / name}: part of the contract but NOT "
                "shipped in hydra-gates/contracts/. A leaf app's tests cannot "
                "load it, which is the gap ADR-084 exists to close."
            )
            continue

        if _read(left) != _read(right):
            findings += 1
            print(
                f"FAIL {CANONICAL_DIR / name}: differs from the copy shipped in "
                "hydra-gates/contracts/. Two definitions of a published contract "
                "is the drift ADR-084 forbids — copy the canonical file over the "
                "shipped one, in the same change."
            )

    print(f"checked {checked} file(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
