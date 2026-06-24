#!/usr/bin/env python3
"""
Extract implemented/reviewed capabilities from an app's OpenSpec directory
into a single docs/features.json, consumed at runtime by the Features &
Roadmap surface (CnFeaturesAndRoadmapPage) and at build time by the
Docusaurus features page.

Reads:  openspec/specs/<slug>/spec.md  (one per capability)
Writes: docs/features.json             (committed to repo by the workflow)

Each emitted entry: { slug, title, summary, docsUrl }.

Only specs whose YAML frontmatter declares status: done are emitted (the
canonical "shipped" status — a capability is done once it has a delivered/
archived change). Other statuses (draft, in-progress, partial, retired,
deprecated, redirect) are skipped.

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


# Map a spec's frontmatter status to a roadmap kind rendered on the features
# page: stable (mint), beta (cobalt blue), soon (orange "coming soon"). Specs
# whose status maps to None are skipped entirely (retired/deprecated/etc.).
STATUS_KIND = {
    "done": "stable", "implemented": "stable", "reviewed": "stable",
    "active": "stable", "stable": "stable",
    "in-progress": "beta", "implementing": "beta", "partial": "beta", "beta": "beta",
    "draft": "soon", "specified": "soon", "proposed": "soon", "planned": "soon",
    "coming-soon": "soon", "soon": "soon",
}

# Tokens to upper-case when title-casing a raw slug (e.g. launchpad-ai → AI).
ACRONYMS = frozenset({
    "ai", "api", "ui", "ux", "or", "bi", "mcp", "tmlo", "mdto", "dcat", "woo",
    "vth", "kcc", "crm", "pdf", "csv", "sepa", "zgw", "ztc", "dso", "rbac",
    "gdpr", "avg", "kvk", "brp", "sso", "jwt", "cli", "ocr", "ner", "kpi",
    "saas", "oas", "json", "xml", "html", "css", "url", "http", "https", "id",
    "pwa", "sip", "eml", "sla", "llm", "rag", "e2e", "qr", "vng",
})

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n(.*)\Z", re.DOTALL)
STATUS_RE = re.compile(r"^status:\s*(.+?)\s*$", re.MULTILINE)
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
PURPOSE_RE = re.compile(r"^##\s+Purpose\s*\n(.+?)(?=\n##\s|\Z)", re.DOTALL | re.MULTILINE)
SLUGGY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")


def titlecase_slug(slug: str) -> str:
    """Turn a kebab slug into a human title, upper-casing known acronyms."""
    return " ".join(
        word.upper() if word in ACRONYMS else word.capitalize()
        for word in slug.split("-")
    )


def clean_title(raw_title: str, slug: str) -> str:
    """Strip 'Spec:' prefixes / 'Specification' suffixes; fall back to a
    title-cased slug when the H1 is missing or is itself a raw slug."""
    title = re.sub(r"^\s*spec:\s*", "", raw_title, flags=re.IGNORECASE)
    title = re.sub(r"\s+specification\s*$", "", title, flags=re.IGNORECASE).strip()
    if not title or title == slug or SLUGGY_RE.match(title):
        title = titlecase_slug(slug)
    return title


def parse_spec(spec_path: Path) -> dict | None:
    """Parse a single spec.md file. Return entry dict or None to skip."""
    text = spec_path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None

    raw_front, body = match.group(1), match.group(2)
    # Read `status` straight off the frontmatter line instead of parsing the
    # whole block as YAML. A typo in an unrelated field (e.g. an unquoted
    # colon in `note:`) makes the block invalid YAML, and a fail-closed YAML
    # parse would then silently drop an otherwise-done spec from the feature
    # list. This mirrors the docusaurus-preset extractFeatures.js so the
    # docs build and CI agree byte-for-byte.
    status_match = STATUS_RE.search(raw_front)
    status = (
        status_match.group(1).strip().strip("\"'").lower()
        if status_match is not None else ""
    )
    kind = STATUS_KIND.get(status)
    if kind is None:
        return None

    slug = spec_path.parent.name

    title_match = H1_RE.search(body)
    raw_title = title_match.group(1).strip() if title_match else slug
    title = clean_title(raw_title, slug)

    summary = ""
    purpose_match = PURPOSE_RE.search(body)
    if purpose_match:
        first_para = purpose_match.group(1).strip().split("\n\n", 1)[0]
        summary = " ".join(first_para.split())

    return {
        "slug": slug,
        "title": title,
        "summary": summary,
        "status": kind,
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
