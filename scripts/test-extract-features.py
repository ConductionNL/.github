"""Regenerating docs/features.json keeps every field the existing file holds.

The app pre-commit hook runs extract-features.py whenever a commit touches
openspec/specs/. The script rebuilt each entry from the overlay or the spec
alone, so a field only the existing file held was dropped on every spec
commit: dossiq's `category`, which its dashboard groups the Features tab by,
went twice and broke DashboardControllerContractTest each time.

These tests run the real script against throwaway app roots.

Usage:
  python3 scripts/test-extract-features.py
  python3 scripts/test-extract-features.py --positive-control

`--positive-control` switches the carry-over off and requires the suite to go
red. A suite that cannot fail is not evidence.
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("extract_features", HERE / "extract-features.py")
ef = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ef)

BREAK = "--positive-control" in sys.argv
if BREAK:
    ef.keep_existing_fields = lambda entries, out_path: entries

FAILURES = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        FAILURES.append(name)


def app(overlay=None, specs=None, existing=None):
    root = Path(tempfile.mkdtemp())
    (root / "openspec" / "specs").mkdir(parents=True)
    (root / "docs").mkdir()
    if overlay is not None:
        (root / "openspec" / "features.overlay.json").write_text(json.dumps(overlay), encoding="utf-8")
    for slug, text in (specs or {}).items():
        d = root / "openspec" / "specs" / slug
        d.mkdir()
        (d / "spec.md").write_text(text, encoding="utf-8")
    if existing is not None:
        (root / "docs" / "features.json").write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return root


def run(root, *extra):
    return ef.main(["--app-root", str(root), *extra])


def read(root):
    return json.loads((root / "docs" / "features.json").read_text(encoding="utf-8"))


OVERLAY = [
    {"slug": "workflow-editor", "title": "Workflow editor", "summary": "Change a process on a canvas.", "status": "stable",
     "title_nl": "Workflow-editor", "summary_nl": "Pas een proces aan op een canvas."},
    {"slug": "woo-publication", "title": "Woo publication", "summary": "Publish decisions.", "status": "beta"},
]

# 1. Every field the existing file holds survives, for every entry.
existing = [
    {"slug": "workflow-editor", "title": "Old title", "summary": "x", "status": "soon", "docsUrl": "d",
     "title_nl": "Workflow-editor", "summary_nl": "Pas een proces aan op een canvas.", "category": "cases", "icon": "Pencil"},
    {"slug": "woo-publication", "title": "Woo publication", "summary": "Publish decisions.", "status": "beta",
     "docsUrl": "openspec/specs/woo-publication/spec.md", "category": "publication"},
]
root = app(overlay=OVERLAY, existing=existing)
run(root)
out = {e["slug"]: e for e in read(root)}
for old in existing:
    missing = set(old) - set(out.get(old["slug"], {}))
    check(f"keeps every existing field of {old['slug']} (missing: {sorted(missing)})", not missing)
check("keeps the category values", out["workflow-editor"].get("category") == "cases" and out["woo-publication"].get("category") == "publication")
check("still regenerates the fields its sources give", out["workflow-editor"]["title"] == "Workflow editor" and out["workflow-editor"]["status"] == "stable")
check("puts carried-over fields after the generated ones", list(out["workflow-editor"])[-2:] == ["category", "icon"])

# 2. The written file passes --check: generation and the CI gate agree.
check("--check accepts the file it just wrote", run(root, "--check") == 0)

# 3. A category in the overlay or in spec frontmatter is emitted, and wins over the old one.
root = app(overlay=[{**OVERLAY[0], "category": "process"}], existing=existing)
run(root)
check("emits an overlay category over the existing one", read(root)[0].get("category") == "process")
spec_md = "---\nstatus: done\ncategory: cases\n---\n# Case list\n\n## Purpose\n\nShows the cases.\n"
root = app(specs={"case-list": spec_md})
run(root)
check("emits a spec frontmatter category", read(root) and read(root)[0].get("category") == "cases")

# 4. A slug that left the sources does not come back from the old file.
root = app(overlay=OVERLAY[:1], existing=existing)
run(root)
check("drops an entry its sources no longer list", [e["slug"] for e in read(root)] == ["workflow-editor"])

if BREAK:
    if not FAILURES:
        print("::error::POSITIVE CONTROL DID NOT FIRE: the carry-over was switched off and every case still passed.")
        sys.exit(1)
    print(f"\nOK: the control fires, {len(FAILURES)} case(s) failed without the carry-over.")
    sys.exit(0)
if FAILURES:
    print(f"\n::error::{len(FAILURES)} failed: regenerating docs/features.json drops or misplaces a field.")
    sys.exit(1)
print("\nall passed")
