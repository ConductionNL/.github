# Playwright MCP Browser Setup

Claude Code drives browsers through [`@playwright/mcp`](https://github.com/microsoft/playwright-mcp). Two things matter for how it is configured:

1. **Claude Code starts every stdio MCP server in `.mcp.json` at session start**, whether or not the session ever touches a browser. A server costs ~60 MB idle (node + the `npm exec` wrapper); the browser itself is only launched on first use.
2. **A Playwright MCP server on a port serves many clients.** Every connection gets its own session and its own isolated browser context, so parallel agents stay separated exactly as they would with one process each.

So the setup is: one browser per project by default, and the seven-browser pool as an opt-in that points at a single shared server.

> Background: on 2026-09-08 Hydra shipped the seven-browser pool as its root `.mcp.json` ([hydra#651](https://github.com/ConductionNL/hydra/pull/651)). Fourteen open Claude Code sessions then held 98 idle MCP processes and ~6 GB, and WSL ran out of memory. Hydra reverted to `browser-1` only and moved the pool to `.claude/mcp/`.

## Default: `browser-1` in `.mcp.json`

Each project ships a `.mcp.json` at its root with a single headless browser. Copy the [example .mcp.json](./examples/.mcp.json.example):

```json
{
  "mcpServers": {
    "browser-1": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest", "--browser", "chromium", "--headless", "--isolated"]
    }
  }
}
```

Hydra ships this file at its repository root (`hydra/.mcp.json`) and the pools under `hydra/.claude/mcp/`. A workspace that symlinks Hydra's `.claude/skills` should symlink both, so the browsers travel with the skills that depend on them:

```bash
ln -sfn /path/to/hydra/.mcp.json   /path/to/workspace/.mcp.json
ln -sfn /path/to/hydra/.claude/mcp /path/to/workspace/.claude/mcp
```

Do **not** put `mcpServers` in `~/.claude/settings.json` — Claude Code ignores that key there ([docs](https://code.claude.com/docs/en/debug-your-config#check-common-causes)).

Project servers from `.mcp.json` need a one-time approval per workspace: accept the workspace-trust dialog when Claude Code first opens the folder, then approve the server from `/mcp` if prompted. No pre-approval settings are required:

- `enableAllProjectMcpServers` only skips that one prompt. Hydra deliberately does not commit `.claude/settings.json` (it is machine-specific, see its `.gitignore`), and Claude Code ignores committed approvals in an untrusted folder anyway ([docs](https://code.claude.com/docs/en/mcp#project-server-approvals-and-workspace-trust)).
- An `mcp__browser-*` allow-list is not needed for parallel sub-agents (`/test-app` Full mode, `/test-counsel`): background subagents surface their permission prompts in the main session, and in auto mode the classifier evaluates their tool calls with the same rules as the main conversation ([subagent permissions](https://code.claude.com/docs/en/sub-agents)).

Then **reload the VS Code window**: `Ctrl+Shift+P` → type `reload window` → Enter.

## Browser pool (parallel agents)

The skills that fan out — `/test-app` Full mode, `/test-counsel`, `opsx-pipeline` — assign one browser per agent:

| Server      | Mode       | Purpose                           |
| ----------- | ---------- | --------------------------------- |
| `browser-1` | Headless   | Main agent (default)              |
| `browser-2` | Headless   | Sub-agent / parallel              |
| `browser-3` | Headless   | Sub-agent / parallel              |
| `browser-4` | Headless   | Sub-agent / parallel              |
| `browser-5` | Headless   | Sub-agent / parallel              |
| `browser-6` | **Headed** | User observation (visible window) |
| `browser-7` | Headless   | Sub-agent / parallel              |

The names are stable; only where the processes come from changed. Hydra keeps two pool files under `.claude/mcp/`:

| File | Shape | When |
| ---- | ----- | ---- |
| `browser-pool-shared.json` | `browser-1`…`browser-5` and `browser-7` are `{"type": "http", "url": "http://localhost:8931/mcp"}`; `browser-6` stays a headed stdio entry | **Recommended.** Zero processes per session; needs the shared server (below) |
| `browser-pool.json` | seven stdio servers | No background process, 7 processes per session. Fallback when the shared server is not installed |

An [example of the shared pool](./examples/browser-pool-shared.json.example) is in this repo. Load a pool for one terminal session:

```bash
# the shared server must be running first — see "The shared server" below
claude --mcp-config .claude/mcp/browser-pool-shared.json
```

### The shared server

Hydra's `scripts/playwright-mcp-server.sh` runs one `@playwright/mcp` process on `localhost:8931` (headless, isolated). Install it once as a systemd user unit so it starts with your WSL session:

```bash
cd /path/to/hydra
scripts/playwright-mcp-server.sh install-service
scripts/playwright-mcp-server.sh status
```

`start` / `stop` / `restart` / `logs` / `uninstall-service` do what they say; `PLAYWRIGHT_MCP_PORT` changes the port (keep the pool file in sync). The server resolves `@playwright/mcp@latest` once, when it starts, so a long-running unit keeps that build until you `restart` it — unlike the old per-session stdio model, where every new session re-resolved `@latest`. The unit pins the `npx` it finds at install time, because a user unit does not load nvm. The headed `browser-6` is deliberately not served by it: a systemd user unit has no WSLg display, and observation browsers are rare enough that a per-session stdio entry is fine.

Two concurrent MCP sessions against one server were verified to get distinct session ids and separate Chromium processes, so the isolation the numbered browsers promise still holds.

### The pool in VS Code

The VS Code extension cannot take `--mcp-config`. Register the URL entries at user scope instead; a URL entry costs a connection, not a process, so this is free per session. The project `.mcp.json` keeps winning for `browser-1`:

```bash
for i in 2 3 4 5 7; do claude mcp add --scope user --transport http "browser-$i" http://localhost:8931/mcp; done
claude mcp add --scope user browser-6 -- npx -y @playwright/mcp@latest --browser chromium --isolated   # headed, on demand
```

Verify with `claude mcp list`. Remove one with `claude mcp remove --scope user browser-N`. If the shared server is down, these entries show as failed in `/mcp` and nothing else breaks.

## Verification

After reload, open the MCP servers panel and check that `browser-1` shows **Connected** (plus whatever pool entries you registered):

- Type `/MCP servers` in the Claude Code chat input
- Or `Ctrl+Shift+P` → search **"MCP servers"**

![MCP servers panel showing browser instances connected](./img/mcp-servers-connected.png)

If a server shows an error, check the output panel: `Ctrl+Shift+P` → **"Output: Focus on Output"** → select **"Claude VSCode"** from the dropdown. For the shared server, `scripts/playwright-mcp-server.sh status` and `journalctl --user -u playwright-mcp.service` are the places to look.

## Usage Rules

1. **Default**: Use `browser-1` for normal work
2. **Parallel agents**: Assign sub-agents `browser-2` through `browser-5` and `browser-7` — and check they are actually loaded first; the pool is opt-in
3. **User watching**: Switch to `browser-6` when the user wants to observe
4. **Fallback**: If a browser errors, try the next numbered browser
5. **Keep `browser-6` reserved**: Only for explicit user observation
