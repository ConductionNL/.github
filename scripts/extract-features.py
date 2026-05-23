#!/usr/bin/env python3
"""
Extract implemented/reviewed capabilities from an app's OpenSpec directory
into a single docs/features.json, consumed at runtime by the Features &
Roadmap surface (CnFeaturesAndRoadmapPage) and at build time by the
Docusaurus features page.

Reads:  openspec/specs/<slug>/spec.md  (one per capability)
Writes: docs/features.json             (committed to repo by the workflow)

Each emitted entry: { slug, title, summary, docsUrl }.

Only specs whose YAML frontmatter declares status: implemented OR reviewed
are emitted. Other statuses (draft, in-progress, deprecated) are skipped.

Stable output: entries sorted by slug; deterministic JSON formatting
(indent=2, sort_keys=False per-entry, trailing newline) so the workflow
only commits when content actually changes.

Exits 0 on success, 1 on missing dependencies, 2 on usage / IO errors.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("error: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(1)


ACCEPTED_STATUSES = frozenset({"implemented", "reviewed"})
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n(.*)\Z", re.DOTALL)
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
PURPOSE_RE = re.compile(r"^##\s+Purpose\s*\n(.+?)(?=\n##\s|\Z)", re.DOTALL | re.MULTILINE)


def parse_spec(spec_path: Path) -> dict | None:
    """Parse a single spec.md file. Return entry dict or None to skip."""
    text = spec_path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None

    raw_front, body = match.group(1), match.group(2)
    try:
        front = yaml.safe_load(raw_front) or {}
    except yaml.YAMLError:
        return None

    if not isinstance(front, dict):
        return None

    status = str(front.get("status", "")).strip().lower()
    if status not in ACCEPTED_STATUSES:
        return None

    slug = spec_path.parent.name

    title_match = H1_RE.search(body)
    raw_title = title_match.group(1).strip() if title_match else slug
    title = re.sub(r"\s+specification\s*$", "", raw_title, flags=re.IGNORECASE).strip()

    summary = ""
    purpose_match = PURPOSE_RE.search(body)
    if purpose_match:
        first_para = purpose_match.group(1).strip().split("\n\n", 1)[0]
        summary = " ".join(first_para.split())

    return {
        "slug": slug,
        "title": title,
        "summary": summary,
        "docsUrl": f"openspec/specs/{slug}/spec.md",
    }


def collect(app_root: Path) -> list[dict]:
    specs_dir = app_root / "openspec" / "specs"
    if not specs_dir.is_dir():
        return []
    entries: list[dict] = []
    for spec_md in sorted(specs_dir.glob("*/spec.md")):
        entry = parse_spec(spec_md)
        if entry is not None:
            entries.append(entry)
    return entries


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--app-root", type=Path, default=Path.cwd(), help="App repo root (default: cwd)")
    parser.add_argument("--out", type=Path, default=None, help="Output path (default: <app-root>/docs/features.json)")
    parser.add_argument("--check", action="store_true", help="Exit 1 if the output would change (CI lint mode)")
    args = parser.parse_args(argv)

    out_path = args.out or (args.app_root / "docs" / "features.json")
    entries = collect(args.app_root)
    payload = json.dumps(entries, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        existing = out_path.read_text(encoding="utf-8") if out_path.is_file() else ""
        if existing != payload:
            print(f"::error::docs/features.json is out of date — run scripts/extract-features.py to regenerate")
            return 1
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")
    print(f"wrote {len(entries)} feature(s) to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
