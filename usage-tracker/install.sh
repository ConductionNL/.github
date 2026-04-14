#!/bin/bash
# Claude Usage Tracker - Quick Install Script
# Run from project root: bash usage-tracker/install.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Installing Claude Usage Tracker..."
echo ""

# Create logs directory (stores machine-readable session snapshots)
mkdir -p "$SCRIPT_DIR/logs"

# Create ~/.local/bin if needed
mkdir -p "${HOME}/.local/bin"

# Make script executable
echo "🔧 Setting permissions..."
chmod +x "$SCRIPT_DIR/claude-usage-tracker.py"
echo "✅ Script is executable"
echo ""

# Create symlink
echo "🔗 Creating symlink..."
if [ -L ~/.local/bin/claude-usage-tracker ]; then
    echo "   ℹ️  Symlink already exists at ~/.local/bin/claude-usage-tracker"
else
    ln -sf "$SCRIPT_DIR/claude-usage-tracker.py" ~/.local/bin/claude-usage-tracker
    echo "✅ Symlink created: ~/.local/bin/claude-usage-tracker"
fi
echo ""

# Check Claude projects dir exists
echo "📁 Checking data source..."
if [ -d "$HOME/.claude/projects" ]; then
    echo "✅ ~/.claude/projects found — tracker has data to read"
else
    echo "⚠️  ~/.claude/projects not found yet."
    echo "   Make at least one Claude Code API call first, then re-run."
fi
echo ""

# Quick test
echo "🧪 Quick self-test..."
if python3 "$SCRIPT_DIR/claude-usage-tracker.py" --help > /dev/null 2>&1; then
    echo "✅ Tracker script works"
else
    echo "❌ Tracker script has errors — check Python 3.8+ is installed"
fi
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "✅ INSTALLATION COMPLETE!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📚 NEXT STEPS:"
echo ""
echo "1️⃣  Test the tracker:"
echo "   python3 usage-tracker/claude-usage-tracker.py --status-bar --all-models"
echo ""
echo "2️⃣  Full report:"
echo "   python3 usage-tracker/claude-usage-tracker.py --all-models"
echo ""
echo "3️⃣  Run continuous monitoring:"
echo "   python3 usage-tracker/claude-usage-tracker.py --monitor --all-models"
echo ""
echo "4️⃣  Set up VS Code task (recommended):"
echo "   • Tasks: Open User Tasks (Ctrl/Cmd + Shift + P)"
echo "   • Paste the task JSON from SETUP.md — auto-starts on workspace open"
echo ""
echo "📖 Read SETUP.md for complete documentation"
echo "════════════════════════════════════════════════════════════════"
echo ""
