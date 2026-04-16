.PHONY: install setup test monitor report clean help

TRACKER_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
TRACKER_SCRIPT := $(TRACKER_DIR)claude-usage-tracker.py

help:
	@echo "Claude Usage Tracker - Makefile Commands"
	@echo "========================================"
	@echo ""
	@echo "Setup:"
	@echo "  make install      - Install tracker script and dependencies"
	@echo "  make setup        - Full setup with VS Code configuration"
	@echo ""
	@echo "Usage:"
	@echo "  make report       - Show one-time usage report"
	@echo "  make status       - Show quick status bar"
	@echo "  make monitor      - Start continuous monitoring"
	@echo "  make monitor-fast - Monitor with 10s refresh"
	@echo ""
	@echo "Maintenance:"
	@echo "  make test         - Test configuration"
	@echo "  make clean        - Clean up logs"
	@echo "  make logs         - Show recent logs"
	@echo ""

install:
	@echo "📦 Installing Claude Usage Tracker..."
	@bash $(TRACKER_DIR)install.sh

setup: install
	@echo ""
	@echo "📋 Setup complete — no VS Code settings changes needed."
	@echo "   The tracker reads ~/.claude/projects/ directly."
	@echo ""
	@echo "✅ Run: make monitor"

test:
	@echo "🧪 Testing configuration..."
	@echo "✓ Checking Claude projects dir: $(HOME)/.claude/projects"
	@if [ -d "$(HOME)/.claude/projects" ]; then \
		echo "  ✅ Projects directory found"; \
	else \
		echo "  ⚠️  Projects directory not found — make at least one Claude Code call first"; \
	fi
	@echo "✓ Testing tracker script..."
	@python3 $(TRACKER_SCRIPT) --help | head -5
	@echo "  ✅ Script works"

report:
	@python3 $(TRACKER_SCRIPT)

status:
	@python3 $(TRACKER_SCRIPT) --status-bar

monitor:
	@python3 $(TRACKER_SCRIPT) --monitor --all-models --interval 300

monitor-fast:
	@python3 $(TRACKER_SCRIPT) --monitor --all-models --interval 10

clean:
	@echo "🧹 Cleaning logs..."
	@rm -f $(TRACKER_DIR)logs/*
	@echo "✅ Cleaned"

logs:
	@echo "📂 Recent tracker logs:"
	@ls -lah $(TRACKER_DIR)logs/ 2>/dev/null || echo "No logs yet"

.DEFAULT_GOAL := help
