#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
"""
gate-118: spec-screens. Every OpenSpec change and spec a PR touches names its
screens.

WHAT THIS CHECKS
----------------
The fleet's screen designs ("boards") live in ConductionNL/design-system under
screens-src/zuiddrecht/<Board>.dc.html. Each app registers its boards in
screens-src/zuiddrecht/apps/<app>.json, and the published set is at
https://identity.conduction.nl/screens. Hydra's "screens first" ADR makes the
board the UI canon: a change says which boards it builds, or says why it has
none.

That statement lives in one file per directory, `screens.md`, next to the
change or spec it belongs to:

    # Screens

    - DqZaaktypen https://identity.conduction.nl/screens/board?id=dossiq/DqZaaktypen
    - No screen: a background job that sends reminder mail; no page changes
    - Design backlog: DqZaakTermijnen (decision 157)

For every directory the PR touches, of these three shapes:

    openspec/changes/<change>/
    openspec/changes/archive/<dated-change>/   (a change being archived)
    openspec/specs/<spec>/

this checker asks five things:

  1. screens.md exists, and has at least one `- ` line.
  2. every `- <Board>` line names a board that exists on design-system main:
     a key of `boards` in the published index preview/screens/screens.json
     (what identity.conduction.nl/screens serves), or a board in the app's own
     registration file screens-src/zuiddrecht/apps/<app>.json, so a board
     registered but not yet built into the index still counts. A board whose
     file screens-src/zuiddrecht/<Board>.dc.html is on main counts too, for
     a board merged before the index was rebuilt. Any app's board
     may be cited: shared boards live under other ids (launchpad's LpStart is
     `werkplek/LpStart`, the shared integrations page is a pipelinq board).
  3. a `- No screen: <reason>` line carries a real reason. A reason that only
     says the design is not there yet ("not designed yet", "no board",
     "design session") is not a reason, it is a missing board: put it on the
     design backlog instead (rule 4). The list is
     design-system's own PLACEHOLDER_REASON, from scripts/screens/
     capabilities.py, copied verbatim so the gate and the board index agree on
     what a placeholder is.
  4. a `- Design backlog: <proposed board> (decision 157)` line passes. It
     marks real UI whose board is not drawn yet, and names the board it
     proposes; only a line that names nothing is a finding.
  5. a `- No board found yet` line is a finding. The generator writes that line
     where it found nothing (decision 150), and a directory a PR touches has to
     settle it: name the board, add one in a paired design-system PR, or give a
     real no-screen reason.

DIFF-SCOPED, AND BLOCKING FROM DAY ONE
--------------------------------------
Board names are validated, not URL text: the first word of a board line is
the board, and the link after it (`https://identity.conduction.nl/screens/
board?id=<app>/<Board>`) is for the reader.

Only directories the change touches are judged (decision 151). There is no
warning period: the gate is meant to land after every app's generated
screens.md has landed, so a red here is always this PR's own directory.

With `--full-tree` (the runner passes it when it audits against the empty
tree, a push whose previous tip is unknown) every live change and spec
directory is judged and archive/ is not: an archived change written before
screens.md existed is history, not a delivery.

HOW THE BOARD LIST IS READ
--------------------------
Read-only, from design-system `main`, once per run:

  HYDRA_GATE_SCREENS_SOURCE     a local directory laid out like the design-system
                                repo root (tests, offline runs, a sparse clone)
  HYDRA_GATE_SCREENS_REPO_URL   the raw base URL, default raw.githubusercontent.com
                                for ConductionNL/design-system main
  HYDRA_GATE_SCREENS_APP        the app name, when neither info.xml nor the
                                repo name matches an apps/<app>.json file

WHY THE INDEX AND NOT ONLY apps/<app>.json. The per-app file is one of several
registration sources build.py merges (rows1/rows2.json and the canvases are the
others). Measured 2026-10-10 on the generated screens.md of dossiq: 185 board
lines named boards that exist and are published, DqZaak among them, but are not
in apps/dossiq.json. Checked against that file alone, the gate would have
failed real boards.

The app name for the optional app file is tried in this order:
HYDRA_GATE_SCREENS_APP, <id> in appinfo/info.xml, the repository name from
GITHUB_REPOSITORY, the origin remote, the directory name. The first one
design-system has a file for wins. App ids are still moving through the fleet
rename, so the info.xml id and the repo name can differ.

A NETWORK FAILURE IS NOT A FINDING
----------------------------------
If design-system cannot be reached, the board lines are unverified. They are
reported as such and the run exits 2 (no verdict) unless a finding that needs
no network already fails it.

Exit codes, the package's status protocol:
  0  every judged directory is clean
  1  at least one finding (count on the summary line)
  2  error: the board list could not be read, or the app dir is unreadable
  3  empty scope: the change touched no openspec change or spec directory
  4  not applicable: no openspec/changes or openspec/specs in this repo

Usage:
  printf '%s\\n' <changed paths> | check_spec_screens.py <app-dir> --changed-stdin
  check_spec_screens.py <app-dir> --full-tree
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exclusion_reason import is_reason_bearing  # noqa: E402

GATE_NUM = 118
GATE_NAME = "spec-screens"

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_ERROR = 2
EXIT_EMPTY_SCOPE = 3
EXIT_NOT_APPLICABLE = 4

DEFAULT_REPO_URL = "https://raw.githubusercontent.com/ConductionNL/design-system/main"

# Copied verbatim from ConductionNL/design-system scripts/screens/capabilities.py
# (PLACEHOLDER_REASON). Keep the two in step: the board index and this gate
# must agree on which reasons only say "not designed yet".
PLACEHOLDER_REASON = re.compile(
    r'not (yet )?designed|not drawn|no board|missing-boards|design session|decision 96|'
    r'nog niet ontworpen|niet getekend|geen bord|no (design|screen) (yet|drawn)', re.I)

# A no-screen reason has to name something. Ten characters is gate-57's floor
# and the one exclusion_reason documents for reasons that must describe a
# subject, not just exist.
REASON_MIN_CHARS = 10

NO_SCREEN_RE = re.compile(r"^no screen\s*:\s*(.*)$", re.I)
NO_BOARD_RE = re.compile(r"^no board found", re.I)
# Decision 157: real UI whose board is not drawn yet goes on the design backlog,
# naming the board it proposes. That passes; the board is owed, and named.
BACKLOG_RE = re.compile(r"^design backlog\s*:\s*(.*)$", re.I)


def scope_dir(path: str) -> str | None:
    """The change or spec directory a changed path belongs to, or None."""
    parts = path.strip().strip("/").split("/")
    if len(parts) < 3 or parts[0] != "openspec":
        return None
    if parts[1] == "specs" and len(parts) >= 4:
        return "/".join(parts[:3])
    if parts[1] == "changes":
        if parts[2] == "archive":
            return "/".join(parts[:4]) if len(parts) >= 5 else None
        if len(parts) >= 4:
            return "/".join(parts[:3])
    return None


def all_live_dirs(app_dir: Path) -> list[str]:
    out: list[str] = []
    for sub in ("changes", "specs"):
        root = app_dir / "openspec" / sub
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if child.is_dir() and not (sub == "changes" and child.name == "archive"):
                out.append(f"openspec/{sub}/{child.name}")
    return out


def norm_board(token: str) -> str:
    token = token.strip().strip("`*").strip()
    token = token.split("/")[-1]
    return re.sub(r"\.dc\.html?$", "", token)


def parse_screens(text: str) -> list[tuple[int, str]]:
    """Return (line number, bullet body) for every `- ` line."""
    out = []
    for n, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if line.startswith("- ") or line.startswith("* "):
            out.append((n, line[2:].strip()))
    return out


def app_candidates(app_dir: Path) -> list[str]:
    names: list[str] = []

    def add(v: str | None) -> None:
        if not v:
            return
        v = v.strip().lower()
        if v.endswith(".git"):
            v = v[:-4]
        v = v.rstrip("/").split("/")[-1]
        if v and v not in names:
            names.append(v)

    add(os.environ.get("HYDRA_GATE_SCREENS_APP"))
    info = app_dir / "appinfo" / "info.xml"
    if info.is_file():
        m = re.search(r"<id>\s*([^<\s]+)\s*</id>", info.read_text(encoding="utf-8", errors="replace"))
        if m:
            add(m.group(1))
    add(os.environ.get("GITHUB_REPOSITORY"))
    try:
        r = subprocess.run(["git", "-C", str(app_dir), "remote", "get-url", "origin"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            add(r.stdout)
    except (OSError, subprocess.SubprocessError):
        pass
    add(app_dir.resolve().name)
    return names


class BoardSource:
    """Reads design-system once per run: the published index, plus the app's own file."""

    INDEX = "preview/screens/screens.json"
    APP_FILE = "screens-src/zuiddrecht/apps/{app}.json"

    def __init__(self) -> None:
        self.local = os.environ.get("HYDRA_GATE_SCREENS_SOURCE")
        self.url = os.environ.get("HYDRA_GATE_SCREENS_REPO_URL", DEFAULT_REPO_URL).rstrip("/")
        self.cache: dict[str, tuple[str, dict]] = {}
        self.errors: list[str] = []

    def _read(self, rel: str) -> tuple[str, dict]:
        """('ok', doc) | ('absent', {}) | ('error', {}). Cached per path."""
        if rel in self.cache:
            return self.cache[rel]
        result: tuple[str, dict] = ("error", {})
        if self.local:
            p = Path(self.local) / rel
            if not p.is_file():
                result = ("absent", {})
            else:
                try:
                    result = ("ok", json.loads(p.read_text(encoding="utf-8")))
                except (OSError, ValueError) as e:
                    self.errors.append(f"{p}: {e}")
        else:
            url = f"{self.url}/{rel}"
            req = urllib.request.Request(url, headers={"User-Agent": "hydra-gates-spec-screens"})
            err = ""
            for _ in range(3):
                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        result = ("ok", json.loads(resp.read().decode("utf-8")))
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        result = ("absent", {})
                        break
                    err = f"{url}: HTTP {e.code}"
                except (urllib.error.URLError, OSError, ValueError) as e:
                    err = f"{url}: {e}"
            if result[0] == "error":
                self.errors.append(err)
        self.cache[rel] = result
        return result

    def board_file_exists(self, board: str) -> str:
        """'ok' | 'absent' | 'error' for screens-src/zuiddrecht/<board>.dc.html.

        The fallback for a board drawn and merged on main whose index has not
        been rebuilt yet and that no apps/<app>.json lists.
        """
        rel = f"screens-src/zuiddrecht/{board}.dc.html"
        if rel in self.cache:
            return self.cache[rel][0]
        status = "error"
        if self.local:
            status = "ok" if (Path(self.local) / rel).is_file() else "absent"
        else:
            req = urllib.request.Request(f"{self.url}/{rel}", method="HEAD",
                                         headers={"User-Agent": "hydra-gates-spec-screens"})
            for _ in range(3):
                try:
                    with urllib.request.urlopen(req, timeout=30):
                        status = "ok"
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        status = "absent"
                        break
                except (urllib.error.URLError, OSError):
                    pass
        self.cache[rel] = (status, {})
        return status

    @staticmethod
    def _app_boards(doc: dict) -> set[str]:
        names = {norm_board(k) for k in (doc.get("boards") or {})}

        def walk(node: object) -> None:
            # rows nest as [id, title, [[board, ...], ...]]; collect every board file name.
            if isinstance(node, list):
                for item in node:
                    walk(item)
            elif isinstance(node, str) and node.endswith(".dc.html"):
                names.add(norm_board(node))

        walk(doc.get("rows") or [])
        return names

    def known_boards(self, candidates: list[str]) -> tuple[bool, set[str], str | None]:
        """(verified, board names, app file used).

        The published index is the authority for "this board exists". The
        app's own registration file is added on top, so a board registered on
        design-system main but not yet built into the index still counts.
        """
        names: set[str] = set()
        verified = False
        status, index = self._read(self.INDEX)
        if status == "ok":
            verified = True
            # Keys are not always the board name: the school sets key a board as
            # `<set>-<Board>` with id `<set>/<Board>`. So the id counts too.
            for key, meta in (index.get("boards") or {}).items():
                names.add(norm_board(key))
                if isinstance(meta, dict) and isinstance(meta.get("id"), str):
                    names.add(norm_board(meta["id"]))
        elif status == "absent":
            self.errors.append(f"{self.INDEX} is missing on design-system main")
        used = None
        for c in candidates:
            st, doc = self._read(self.APP_FILE.format(app=c))
            if st == "ok":
                names |= self._app_boards(doc)
                used = c
                verified = True
                break
        return verified, names, used


def run(app_dir: Path, dirs: list[str]) -> int:
    source = BoardSource()
    candidates = app_candidates(app_dir)
    known: tuple[bool, set[str], str | None] | None = None

    findings: list[str] = []
    unverified: list[str] = []
    counts = {"dirs": 0, "boards": 0, "noscreen": 0, "backlog": 0}

    for d in dirs:
        counts["dirs"] += 1
        screens = app_dir / d / "screens.md"
        rel = f"{d}/screens.md"
        if not screens.is_file():
            findings.append(
                f"{d}/: no screens.md. Name the boards this builds (`- <Board> <url>`), "
                f"or `- No screen: <reason>` when nothing a user sees changes.")
            continue
        bullets = parse_screens(screens.read_text(encoding="utf-8", errors="replace"))
        if not bullets:
            findings.append(f"{rel}: has no `- ` line, so it names neither a board nor a reason.")
            continue
        for n, body in bullets:
            if NO_BOARD_RE.match(body):
                findings.append(
                    f"{rel}:{n}: `No board found yet`. This PR touches the directory, so settle it: "
                    f"name the board, add one in a paired design-system PR, put it on the design backlog "
                    f"(`- Design backlog: <proposed board> (decision 157)`), or give a real no-screen reason.")
                continue
            bm = BACKLOG_RE.match(body)
            if bm:
                counts["backlog"] += 1
                proposed = re.sub(r"\(decision 157\)\s*$", "", bm.group(1), flags=re.I).strip()
                if not is_reason_bearing(proposed):
                    findings.append(
                        f"{rel}:{n}: `Design backlog` without the board it proposes. "
                        f"Write `- Design backlog: <proposed board> (decision 157)`.")
                continue
            m = NO_SCREEN_RE.match(body)
            if m:
                counts["noscreen"] += 1
                reason = m.group(1).strip()
                if not is_reason_bearing(reason, min_chars=REASON_MIN_CHARS):
                    findings.append(f"{rel}:{n}: `No screen` without a real reason ({reason!r}).")
                elif PLACEHOLDER_REASON.search(reason):
                    findings.append(
                        f"{rel}:{n}: `No screen: {reason}` only says the design is not there yet. "
                        f"That is a missing board: draw it in a paired design-system PR, or write "
                        f"`- Design backlog: <proposed board> (decision 157)`.")
                continue
            counts["boards"] += 1
            words = body.split()
            board = norm_board(words[0])
            if known is None:
                known = source.known_boards(candidates)
            verified, boards, _used = known
            if not verified:
                unverified.append(f"{rel}:{n}: board {board!r} not verified, design-system was unreachable.")
                continue
            if board not in boards and "/" not in words[0]:
                fstatus = source.board_file_exists(board)
                if fstatus == "ok":
                    continue
                if fstatus == "error":
                    unverified.append(f"{rel}:{n}: board {board!r} not verified, design-system was unreachable.")
                    continue
            if board not in boards:
                findings.append(
                    f"{rel}:{n}: board {board!r} is not on design-system main (not in "
                    f"preview/screens/screens.json, not in the app's screens-src/zuiddrecht/apps/ file, "
                    f"and no screens-src/zuiddrecht/{board}.dc.html). "
                    f"Use a board that exists, or add it in a paired design-system PR.")

    for f in findings:
        print(f"  {f}")
    for u in unverified:
        print(f"  UNVERIFIED {u}")
    for e in source.errors:
        print(f"  design-system read error: {e}")
    print(f"[gate-{GATE_NUM}] {GATE_NAME}: checked {counts['dirs']} dir(s), "
          f"{counts['boards']} board line(s), {counts['noscreen']} no-screen line(s), "
          f"{counts['backlog']} design-backlog line(s), "
          f"{len(findings)} finding(s), {len(unverified)} unverified.")
    if findings:
        print(f"[gate-{GATE_NUM}] {GATE_NAME}: FAIL: {len(findings)} finding(s)")
        return EXIT_FAIL
    if unverified:
        print(f"[gate-{GATE_NUM}] {GATE_NAME}: NO VERDICT: {len(unverified)} board line(s) "
              f"could not be checked against design-system")
        return EXIT_ERROR
    return EXIT_PASS


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("app_dir")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--changed-stdin", action="store_true",
                      help="read the changed paths, one per line, from stdin")
    mode.add_argument("--full-tree", action="store_true",
                      help="judge every live change and spec directory (archive/ excluded)")
    args = ap.parse_args(argv)

    app_dir = Path(args.app_dir)
    if not app_dir.is_dir():
        print(f"[gate-{GATE_NUM}] {GATE_NAME}: ERROR: {app_dir} is not a readable directory.")
        return EXIT_ERROR
    if not (app_dir / "openspec" / "changes").is_dir() and not (app_dir / "openspec" / "specs").is_dir():
        print(f"[gate-{GATE_NUM}] {GATE_NAME}: NOT APPLICABLE: no openspec/changes or openspec/specs.")
        return EXIT_NOT_APPLICABLE

    if args.full_tree:
        dirs = all_live_dirs(app_dir)
    else:
        seen: list[str] = []
        for line in sys.stdin.read().splitlines():
            d = scope_dir(line)
            # A directory the change deleted, or moved away (a change being
            # archived leaves its old path behind), is not judged at its old path.
            if d and d not in seen and (app_dir / d).is_dir():
                seen.append(d)
        dirs = seen
    if not dirs:
        print(f"[gate-{GATE_NUM}] {GATE_NAME}: EMPTY SCOPE: no openspec change or spec directory in scope.")
        return EXIT_EMPTY_SCOPE
    return run(app_dir, dirs)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
