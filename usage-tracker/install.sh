#!/bin/bash
# Claude Usage Tracker - Quick Install Script
# Run from project root: bash usage-tracker/install.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${HOME}/.claude/usage-tracker"

echo "🚀 Installing Claude Usage Tracker..."
echo ""

# Create centralized data directory
echo "📁 Creating data directory..."
mkdir -p "$DATA_DIR"
echo "✅ Data directory: $DATA_DIR"
echo ""

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
    existing_target=$(readlink -f ~/.local/bin/claude-usage-tracker 2>/dev/null)
    expected_target=$(readlink -f "$SCRIPT_DIR/claude-usage-tracker.py" 2>/dev/null)
    if [ "$existing_target" = "$expected_target" ]; then
        echo "   ℹ️  Symlink already exists and points to the correct target"
    else
        echo "   ⚠️  Symlink exists but points to: $existing_target"
        echo "   🔄 Updating to: $expected_target"
        ln -sf "$SCRIPT_DIR/claude-usage-tracker.py" ~/.local/bin/claude-usage-tracker
        echo "✅ Symlink updated"
    fi
else
    ln -sf "$SCRIPT_DIR/claude-usage-tracker.py" ~/.local/bin/claude-usage-tracker
    echo "✅ Symlink created: ~/.local/bin/claude-usage-tracker"
fi
echo ""

# Migrate old per-project data if it exists
if [ -f "$SCRIPT_DIR/limits.json" ] && [ ! -f "$DATA_DIR/limits.json" ]; then
    echo "📦 Migrating limits.json to central location..."
    cp "$SCRIPT_DIR/limits.json" "$DATA_DIR/limits.json"
    echo "✅ Migrated: $DATA_DIR/limits.json"
fi
if [ -f "$SCRIPT_DIR/logs/session-state.json" ] && [ ! -f "$DATA_DIR/session-state.json" ]; then
    echo "📦 Migrating session-state.json to central location..."
    cp "$SCRIPT_DIR/logs/session-state.json" "$DATA_DIR/session-state.json"
    echo "✅ Migrated: $DATA_DIR/session-state.json"
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
echo "2️⃣  Calibrate from claude.ai/settings/usage:"
echo "   python3 usage-tracker/claude-usage-tracker.py --calibrate \\"
echo "     --session-pct 27 --weekly-all-pct 3 --session-reset '1h 48m' --weekly-all-reset 'fri:08'"
echo ""
echo "3️⃣  Run continuous monitoring:"
echo "   python3 usage-tracker/claude-usage-tracker.py --monitor --all-models"
echo ""
echo "📖 Read CALIBRATE.md for calibration guide"
echo "📖 Read SETUP.md for complete documentation"
echo ""
echo "📁 Data location: $DATA_DIR"
echo "════════════════════════════════════════════════════════════════"
echo ""
