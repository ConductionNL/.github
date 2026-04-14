# Parallel Agents & Subscription Cap

Running commands that spawn multiple agents simultaneously (like `/test-counsel`, `/test-app`, `/feature-counsel`) consumes your Claude subscription usage much faster than normal conversations. This guide explains why and how to use these commands responsibly.

## Why Parallel Agents Drain Your Cap Fast

Every Claude Code API call sends the following with it:
- **CLAUDE.md** — workspace instructions
- **MEMORY.md** — persistent memory index
- **The full conversation history** so far

When you run a command that launches 8 agents in parallel, all 8 agents start simultaneously, and each one makes many tool calls internally (file reads, browser snapshots, API calls). That means those files above get sent dozens to hundreds of times within a few minutes.

**Example: `/test-counsel` on a single project**
- 8 agents × ~30 tool calls each = ~240 API calls
- Each call carries CLAUDE.md + MEMORY.md + the agent's conversation history
- This can consume as much as a full day of normal usage in one run

When you see: `You've hit your limit · resets 3pm (Europe/Amsterdam)` — that's your Claude subscription's rolling usage cap, not a rate limit.

## Commands That Use Parallel Agents

| Command | Agents | Cap Impact |
|---------|--------|------------|
| `/test-counsel` | 8 agents | Very high — use sparingly |
| `/feature-counsel` | 8 agents | Very high — use sparingly |
| `/test-app` (Full mode) | 6 agents | High — use sparingly |
| `/test-app` (Quick mode) | 1 agent | Low — fine to use regularly |
| `/test-scenario-run` (multiple) | up to 5 agents | Medium — depends on scenario count |
| `/test-scenario-run` (single) | 1 agent | Low — fine to use regularly |
| `/opsx-pipeline` | 1–5 agents per batch | Medium to Very high — depends on number of changes and model selected |
| `/opsx-apply` | 1 agent | Low — fine to use regularly |
| Single `/test-persona-*` | 1 agent | Low — fine to use regularly |

## Guidelines for Careful Use

**Open a fresh window before running:**
Start the command in a new Claude Code window (no prior conversation history). The full conversation history is sent with every API call — in a window with 30+ prior messages, that history alone multiplies the token cost significantly across all parallel agents. A fresh window has zero history overhead.

**Before running a multi-agent command:**
- Check the clock — do you have enough session left, or will you need Claude for other work today?
- Prefer Quick mode over Full mode in `/test-app` unless you need the full perspective sweep
- Run individual persona testers (`/test-persona-henk`, etc.) instead of the full `/test-counsel` when you only need one perspective

**Don't run these commands:**
- Multiple times in a row on the same day
- Right before needing Claude for urgent implementation work
- Just to "see what happens" — run them when you have a concrete need for the output

**After hitting the cap:**
- The limit resets at a fixed time (shown in the message, e.g. `resets 3pm (Europe/Amsterdam)`)
- Wait for the reset before continuing — there's no workaround
- Use the waiting time to review output that was already generated

## Files to Keep Lean

These files are sent with **every single API call** in the workspace. In a parallel-agent run they are multiplied by the number of agents and the number of tool calls each agent makes. Keep them minimal.

| File | Purpose | Target size |
|------|---------|-------------|
| `.claude/CLAUDE.md` | Workspace instructions for Claude | < 100 lines |
| `.claude/MEMORY.md` | Index of memory files | < 50 lines (index only, no content) |

**Rules:**
- **CLAUDE.md**: Only include instructions Claude needs on every task. Move niche/infrequent knowledge to separate files in `.claude/docs/` that can be read on demand.
- **MEMORY.md**: This is an index only — one line per memory file with a brief description. Never write memory content directly into MEMORY.md.
- **Persona files** (`personas/*.md`): These are only loaded when a sub-agent explicitly reads them — they don't auto-load. Keep them focused, but they don't need to be ultra-short.

## Two Kinds of Token Limits

Claude has two separate token limits that are easy to confuse:

### Context window (per-conversation limit)

The maximum tokens a model can process in a **single conversation**. This is a fixed technical limit of the model itself. If a conversation exceeds it, older messages are compressed or dropped. You never "run out" of context window across conversations — each conversation starts fresh.

| Model     | Context window | Max output  |
|-----------|---------------|-------------|
| Haiku 4.5 | 200k tokens   | 64k tokens  |
| Sonnet 4.6| 1M tokens     | 64k tokens  |
| Opus 4.6  | 1M tokens     | 128k tokens |

> **Source:** [Anthropic models overview](https://platform.claude.com/docs/en/about-claude/models/overview)

### Subscription quota (account-level limit)

The total tokens you can use across **all conversations combined** within a rolling time window. When you hit this, you see *"You've hit your limit - resets 3pm"*. Cheaper models allow more total tokens before hitting the cap:

| Model  | Session (~5h) | Weekly (~7d) |
|--------|--------------|-------------|
| Haiku  | ~1.2M tokens | ~6M tokens  |
| Sonnet | ~400K tokens | ~2M tokens  |
| Opus   | ~200K tokens | ~1M tokens  |

These are approximate estimates — Anthropic does not publish exact numbers. Calibrate your own values using [claude.ai/settings/usage](https://claude.ai/settings/usage) (see the [usage tracker setup guide](../../usage-tracker/SETUP.md)).

### Why this matters for parallel agents

A 3-agent parallel run with Haiku might use ~90K tokens total. That fits easily in Haiku's 200k context window per agent, but it consumes ~7.5% of your ~1.2M session quota. The same run with Opus uses similar tokens but that's ~45% of your ~200K session quota. **The context window is rarely the bottleneck — the subscription quota is.**

## Model Selection

All parallel sub-agent skills ask which model to use at run time. **Haiku is the default and recommended choice** for parallel runs — it costs significantly less from your subscription quota than Sonnet or Opus.

| Model                    | Context window | Cap cost | Best for                                                          |
|--------------------------|---------------|----------|-------------------------------------------------------------------|
| **Haiku 4.5 (default)** | 200k tokens   | Lowest   | Most parallel test runs — broad coverage, fast, quota-efficient   |
| **Sonnet 4.6**          | 1M tokens     | Higher   | Browser-heavy tasks with many snapshots, or nuanced analysis      |
| **Opus 4.6**            | 1M tokens     | Highest  | Final pre-release testing or critical targeted reviews            |

Skills that ask for a model choice when launching agents:
- `/test-counsel` — 8 agents (one per persona)
- `/feature-counsel` — 8 agents (one per persona)
- `/test-app` (Full mode) — 6 agents (one per perspective)
- `/opsx-pipeline` — 1–5 agents (model selectable per change or uniformly for all)
- `/test-scenario-run` — Haiku by default, Sonnet optional (asked per run)

**Choosing Sonnet or Opus:** Both have a 1M context window vs Haiku's 200k. For browser-heavy tasks that process many page snapshots or read large files, Sonnet's larger context is an advantage. Reserve Opus for final pre-release sweeps or critical targeted reviews where maximum reasoning depth matters.

The main conversation (where you type commands) always uses whichever model you have active. Only the sub-agents use the model you select when prompted.

For guidance on which testing commands to use and when, see [testing.md](testing.md).

## Monitor Your Live Usage

The [usage tracker](../../usage-tracker/README.md) lets you watch your token consumption in real time from a terminal panel in VS Code — useful for knowing how much cap you have left before starting a parallel-agent run.

```bash
# One-line status check
python3 usage-tracker/claude-usage-tracker.py --status-bar

# Live monitoring (30s refresh)
python3 usage-tracker/claude-usage-tracker.py --monitor
```

The tracker reads Claude Code's session files (`~/.claude/projects/`) directly and is accurate for API token counts. The **limit thresholds** are approximate — verify your real cap at [claude.ai/settings/usage](https://claude.ai/settings/usage). Setup instructions: [`usage-tracker/SETUP.md`](../../usage-tracker/SETUP.md).
