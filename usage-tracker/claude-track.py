#!/usr/bin/env python3
"""
Quick launcher for Claude Usage Tracker
Provides convenient CLI interface for all tracking modes.
"""

import sys
import argparse
import importlib.util
from pathlib import Path


def load_tracker():
    tracker_path = Path(__file__).parent / "claude-usage-tracker.py"
    if not tracker_path.exists():
        print(f"❌ Tracker script not found at {tracker_path}")
        print("Run: bash usage-tracker/install.sh")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("claude_usage_tracker", tracker_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    parser = argparse.ArgumentParser(
        prog="claude-track",
        description="Claude Usage Tracker for VS Code",
        epilog="Use: claude-track report | claude-track monitor | claude-track status"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("report", help="Show full usage report")
    subparsers.add_parser("status", help="Show status bar format")

    monitor_parser = subparsers.add_parser("monitor", help="Start continuous monitoring")
    monitor_parser.add_argument(
        "--interval", type=int, default=300,
        help="Refresh interval in seconds (default: 300 = 5 minutes)"
    )
    monitor_parser.add_argument(
        "-f", "--fast", action="store_true",
        help="Fast mode (10 second interval)"
    )

    subparsers.add_parser("setup", help="Run installation & setup")
    subparsers.add_parser("info", help="Show configuration info")

    args = parser.parse_args()

    if args.command == "report":
        mod = load_tracker()
        tracker = mod.ClaudeUsageTracker()
        tracker.print_report(all_models=True)

    elif args.command == "status":
        mod = load_tracker()
        tracker = mod.ClaudeUsageTracker()
        tracker.print_status_bar(all_models=True)

    elif args.command == "monitor":
        interval = 10 if args.fast else args.interval
        mod = load_tracker()
        tracker = mod.ClaudeUsageTracker()
        tracker.monitor_continuous(interval=interval, all_models=True)

    elif args.command == "setup":
        import subprocess
        setup_script = Path(__file__).parent / "install.sh"
        subprocess.run(["bash", str(setup_script)])

    elif args.command == "info":
        projects_dir = Path.home() / ".claude" / "projects"
        tracker_path = Path(__file__).parent / "claude-usage-tracker.py"
        limits_path = Path(__file__).parent / "limits.json"

        print("🔍 Claude Usage Tracker — Configuration Info\n")
        print(f"📍 Tracker script : {tracker_path}")
        print(f"✅ Script exists  : {tracker_path.exists()}")

        print(f"\n📁 Projects dir   : {projects_dir}")
        print(f"✅ Dir exists     : {projects_dir.exists()}")
        if projects_dir.exists():
            jsonl_files = list(projects_dir.glob("**/*.jsonl"))
            print(f"✅ JSONL files    : {len(jsonl_files)}")

        print(f"\n⚙️  Limits file    : {limits_path}")
        print(f"✅ Configured     : {limits_path.exists()}")
        if not limits_path.exists():
            print("   ⚠️  Copy limits.example.json → limits.json and edit values")

        print("\n📖 Documentation  : usage-tracker/SETUP.md")
        print("🆘 Help           : claude-track -h")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
