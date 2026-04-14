# Local LLM Setup (Ollama + Qwen)

Claude Code can run with a **local LLM** instead of the Anthropic API, using [Ollama](https://ollama.com/) and Alibaba's [Qwen3-Coder](https://ollama.com/library/qwen3-coder) model. Ollama v0.14.0+ includes built-in Anthropic Messages API compatibility, so Claude Code connects to it without any proxy or adapter.

## When to use local vs Claude API

| Use case | Recommendation |
|----------|---------------|
| **Data sovereignty** — code or data must stay in the EU / on-premise | Local Qwen |
| **Security-sensitive work** — credentials, private APIs, client data | Local Qwen |
| **Offline / air-gapped environments** | Local Qwen |
| **Simple tasks** — formatting, renaming, small refactors, boilerplate | Local Qwen |
| **Cost reduction** — high-volume, repetitive prompts | Local Qwen |
| **Complex reasoning** — architecture, debugging, multi-file changes | Claude API |
| **Large context** — analyzing entire codebases or long specs | Claude API |
| **Quality-critical** — production code, specs, client deliverables | Claude API |

> **Rule of thumb:** Use Qwen locally for work that is private, simple, or high-volume. Use Claude API when quality and reasoning depth matter most. You can switch between them freely — they use the same Claude Code interface, tools, and commands.

## Step 1: Install Ollama

Install Ollama **natively on WSL** (not in Docker — native gives better GPU passthrough and performance):

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Ollama runs as a background service automatically. Verify it's running:

```bash
ollama --version    # Should show 0.14.0+
```

## Step 2: Pull a Qwen model

Choose the right model for your GPU VRAM:

| Model | Download | Size | Min VRAM | Speed (RTX 3070) | Tool calling? |
|-------|----------|------|----------|-------------------|---------------|
| `qwen3:8b` | `ollama pull qwen3:8b` | 5.2 GB | 8 GB (fits 100%) | ~12s | **No** (chat only) |
| **`qwen3:14b`** | `ollama pull qwen3:14b` | **9.3 GB** | 12 GB | **~2min** (spills to CPU on 8GB) | **Yes** |
| `qwen3-coder` | `ollama pull qwen3-coder` | 18 GB | 24 GB | ~6min (mostly CPU on 8GB) | Yes |

**Recommended: `qwen3:14b`** — the smallest model that supports **tool calling** (reading files, editing code, running commands). On 8GB VRAM it's slow (~2min/response) but works as a batch/overnight agent. On 12GB+ VRAM it runs at interactive speed (~15s).

```bash
ollama pull qwen3:14b
```

> **Why not `qwen3:8b`?** It's faster but can only chat — it cannot use tools (file access, shell commands, code editing). The model is too small to reliably produce the structured function-call format that CLI agents require. It will show its thinking but won't execute anything.
>
> **Why not `qwen3-coder`?** It's the most capable (30B params) but requires 24GB+ VRAM. On an 8GB GPU it runs ~68% on CPU and takes ~6 minutes per response. Only use it with a workstation GPU (RTX 4090, A6000, etc).

Check your available memory:

```bash
free -h           # Look at the "available" column
nvidia-smi        # Check GPU VRAM
```

If you don't have enough system memory, increase the WSL allocation. On **Windows**, edit (or create) `%USERPROFILE%\.wslconfig`:

```ini
[wsl2]
memory=24GB
```

Then restart WSL from PowerShell:

```powershell
wsl --shutdown
```

Reopen your Ubuntu terminal — the new memory limit is now active.

## Step 3: Run Claude Code with Qwen

Open a **new terminal** and run (replace model name with whichever you pulled):

```bash
ANTHROPIC_BASE_URL=http://localhost:11434 ANTHROPIC_API_KEY=ollama claude --model qwen3:14b
```

This opens the full interactive Claude Code CLI — same interface, same tools, same commands — but powered by Qwen running locally on your machine. No data leaves your workstation.

For a quick **one-shot prompt** (no interactive session):

```bash
ANTHROPIC_BASE_URL=http://localhost:11434 ANTHROPIC_API_KEY=ollama claude --model qwen3:14b --print "explain this function"
```

## Running local and API side by side

The env vars are **scoped to that single terminal window only**. This means you can run both simultaneously:

- **Terminal 1** — Qwen locally (free, private, slower) doing a long-running task like a bulk refactor or code review
- **Terminal 2 / VS Code** — Claude API (fast, powerful) for your main interactive development work

This is the recommended workflow: **sidecar the free local model** for background tasks while you continue your normal work with Claude API at full speed. The local session won't affect your API session in any way — they're completely independent.

```
┌─────────────────────────┐  ┌─────────────────────────┐
│  Terminal 1 (Qwen)      │  │  VS Code / Terminal 2   │
│                         │  │                         │
│  Free, local, private   │  │  Claude API (Opus)      │
│  Running: bulk refactor │  │  Fast interactive dev   │
│  Speed: ~15 tok/s       │  │  Speed: ~50-80 tok/s    │
│  Cost: $0               │  │  Cost: normal API usage │
│                         │  │                         │
│  ► Background task      │  │  ► Your main work       │
└─────────────────────────┘  └─────────────────────────┘
```

To go back to Claude API in any terminal, simply open a new terminal as normal — no env vars to unset.

## Performance expectations

Benchmarked on an RTX 3070 (8GB VRAM) with 24GB WSL memory:

| Model | Simple task | Tool calling | Fits in 8GB VRAM | Usable interactively? |
|-------|-------------|-------------|------------------|----------------------|
| qwen3:8b | ~12 seconds | No | Yes (100% GPU) | Chat only |
| **qwen3:14b** | **~2 minutes** | **Yes** | No (spills to CPU) | **Batch/overnight** |
| qwen3-coder (30B) | ~6 minutes | Yes | No (68% CPU) | No |
| Claude API (Opus) | ~3 seconds | Yes | N/A (cloud) | Yes |

**Be honest about the trade-off:** The recommended local model (`qwen3:14b`) is **~40x slower** than Claude API on 8GB VRAM hardware. It's not viable for interactive coding — but it **does support tool calling**, which makes it a real coding agent that can read files, edit code, and run commands. Use it for batch jobs you kick off and walk away from (e.g., overnight PHPCS fixes, bulk refactors, code reviews).

**Where local shines:**
- **Nightly / batch jobs** — automated code reviews, linting suggestions, documentation generation, bulk refactors where you kick it off and walk away
- **Cost** — completely free, no API usage, no token limits, run it as much as you want
- **Privacy** — nothing leaves your machine, ideal for client code under NDA or government data
- **Simple interactive tasks** — quick renames, formatting, boilerplate generation where the speed difference barely matters

## Alternative: Qwen Code CLI (native Qwen experience)

Qwen has its own dedicated CLI tool (v0.11+) with an interface similar to Claude Code, optimized for Qwen models:

```bash
sudo npm install -g @qwen-code/qwen-code@latest
```

**Configure it to use your local Ollama** by editing `~/.qwen/settings.json`:

```json
{
  "modelProviders": {
    "openai": [
      {
        "id": "qwen3:14b",
        "name": "Qwen3 14B (Local Ollama)",
        "envKey": "OLLAMA_API_KEY",
        "baseUrl": "http://localhost:11434/v1"
      }
    ]
  },
  "security": {
    "auth": {
      "selectedType": "openai"
    }
  },
  "env": {
    "OLLAMA_API_KEY": "ollama"
  },
  "model": {
    "name": "qwen3:14b"
  }
}
```

> Adjust the model `id` and `name` if you pulled a different model (e.g., `qwen3:8b` for chat-only, or `qwen3-coder` on 24GB+ VRAM).

The key parts: `security.auth.selectedType: "openai"` bypasses the OAuth prompt, `modelProviders.openai` tells Qwen Code where your local Ollama lives, and `env.OLLAMA_API_KEY` provides the dummy API key that Ollama ignores but Qwen Code requires.

**Launch it:**

```bash
cd /path/to/your-project
qwen
```

**Tool calling requires `qwen3:14b` or larger.** The `qwen3:8b` model runs in chat-only mode — it can reason and answer questions but cannot use tools (no file access, no shell commands, no code editing). The `qwen3:14b` model supports structured tool calling and works as a full coding agent, though it's slow on 8GB VRAM (~2min/response). On 12GB+ VRAM it runs at interactive speed.

**Sharing context with Claude Code:** Qwen Code reads `QWEN.md` instead of `CLAUDE.md`, but supports `@path/to/file.md` imports. You can create a `QWEN.md` in the workspace root that imports the Claude configuration:

```markdown
@CLAUDE.md
@CLAUDE.local.md
```

This gives Qwen Code the same project context, coding standards, and credentials as Claude Code. However, Qwen Code does **not** support Claude's `/opsx-*` slash commands or skills — those are Claude Code-specific. For the full OpenSpec workflow, use Claude Code (with either API or local Qwen backend).

## Tips

- **Don't close the terminal** where Ollama is running — if Ollama stops, your Claude Code session loses its backend
- **One model at a time** — Ollama loads/unloads models automatically, but running two large models simultaneously will OOM
- **VS Code extension** still uses Claude API — the env var trick only works for the CLI. This is fine: use VS Code for complex work (Claude API) and terminal for quick local tasks (Qwen)
- **All Claude Code features work** — tools, file editing, git, commands, skills, browser MCP — because the interface is the same, only the model backend changes

## Troubleshooting

### Ollama model won't load (out of memory)

Increase WSL memory in `%USERPROFILE%\.wslconfig`:

```ini
[wsl2]
memory=24GB
```

Then restart WSL from PowerShell: `wsl --shutdown`

---

## Double Dutch (RAD Workflow)

A two-shift Rapid Application Development cycle that pairs Claude (daytime, fast, cloud) with Qwen (overnight, slow, local/free).

```
         09:00                    17:00                   09:00
           |                        |                       |
  ┌────────┴────────────────────────┴───────────────────────┴──
  │  REVIEW    ◄── DAY SHIFT (Claude) ──►    HANDOFF    NIGHT SHIFT (Qwen)
  │  Qwen's        Specs, architecture,      Prepare     PHPCS fixes,
  │  output         complex logic,           task files   boilerplate,
  │                 code review, PRs                      bulk refactors,
  │                                                       test generation
  └────────────────────────────────────────────────────────────
```

### Daily Cycle

**Morning (09:00)** — Review Qwen's overnight output: code changes, test results, PHPCS fixes. Accept or reject changes, note issues for the day's work.

**Day (09:00-17:00)** — Spec work with Claude: clarify requirements, write OpenSpec artifacts (`/opsx-ff`, `/opsx-new` → `/opsx-continue`), design architecture, solve hard problems, review PRs. Claude handles the thinking.

**Evening (17:00)** — Hand off to Qwen: prepare self-contained task files (e.g., `qwen-phpcs-task.md`) with specific, mechanical work. Start Qwen batch and leave overnight.

### Division of Labor

| | Claude (Day) | Qwen (Night) |
|---|---|---|
| **Strengths** | Reasoning, architecture, specs, multi-file design | Mechanical fixes, repetitive changes, bulk ops |
| **Speed** | ~3s/response (cloud API) | ~2min/response (local 14b on 8GB VRAM) |
| **Cost** | API tokens (Max plan) | Free (local GPU) |
| **Best for** | Complex logic, code review, client deliverables | PHPCS fixes, boilerplate, test scaffolding |

### Task File Format

Qwen works best with narrow, explicit task files. Example:

```markdown
# Task: Fix PHPCS Named Parameter Errors

Working directory: `/path/to/app`

## Files to fix
1. `lib/Controller/FooController.php` (3 errors)
2. `lib/Service/BarService.php` (1 error)

## How to fix
Find function calls without named parameters. Look up the method signature
and add the parameter name:
- BEFORE: `$this->setName('value')` where signature is `setName(string $name)`
- AFTER: `$this->setName(name: 'value')`

## Verification
Run: `./vendor/bin/phpcs --standard=phpcs.xml <files>`
Expected: 0 errors
```

### Running Qwen Overnight

```bash
# Terminal 1 — start Qwen with Claude Code CLI
ANTHROPIC_BASE_URL=http://localhost:11434 ANTHROPIC_API_KEY=ollama \
  claude --model qwen3:14b

# Then paste or reference the task file
```

> **Requires `qwen3:14b` or larger** for tool calling (file editing, shell commands). See [Step 2](#step-2-pull-a-qwen-model) for details.

> **Known limitation:** Tool calling via CLI is unreliable with local models when system prompts are large. For now, Qwen works best on tasks where it can output code changes as text that you review and apply manually in the morning.
