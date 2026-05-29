# Codeberg Authentication Setup (WSL + VS Code + Claude Code)

This guide takes you from a fresh WSL install to a fully-authenticated Codeberg workstation, so every tool you use — `git` from any shell, VS Code's source control panel, the Gitea extension, the `tea` CLI, and Claude Code's Bash tool — can clone, push, and create pull requests on Codeberg without re-authenticating.

The setup is two layers:

1. **SSH key** — handles all `git` operations (clone, fetch, push, pull). Authenticated once per WSL reboot via `keychain` + the passphrase.
2. **`tea` CLI + API token** — handles PR/issue/label operations that aren't part of the git protocol (creating PRs, posting comments, listing issues). Authenticated once per machine; the token sits in `~/.config/tea/config.yml` from then on.

Once both are configured, Claude Code can drive the entire Codeberg workflow inside your existing session — no extra prompts, no token paste-ins.

> **Why Codeberg?** Conduction migrated from `github.com/ConductionNL` to `codeberg.org/Conduction` in May 2026. Codeberg runs Forgejo (a Gitea fork) — a community-owned, EU-hosted alternative to GitHub. The platform-preference order is **Codeberg primary, GitHub secondary, GitLab alternative**. Hydra and all migrated skills still understand GitHub URLs, so older repos and PR links continue to work.

## Prerequisites

- WSL2 with Ubuntu (see [Workstation Setup](./workstation-setup.md) → "Install WSL2")
- A Codeberg account at <https://codeberg.org>
- Membership in the `Conduction` organisation (ask a maintainer if you're missing access)
- VS Code with the Remote WSL extension installed on the Windows side

## Step 1 — Generate an SSH key

In your WSL terminal:

```bash
ssh-keygen -t ed25519 -C "your.name@conduction.nl" -f ~/.ssh/id_ed25519_codeberg
```

- **Algorithm**: ED25519 — small, fast, modern. Don't use RSA unless you have a specific compatibility reason.
- **Filename**: `id_ed25519_codeberg` — explicit name so you can have separate keys per host (one for Codeberg, one for GitHub, etc.) without them colliding.
- **Passphrase**: **enter one**. A passphraseless key on disk is a stand-alone credential — anyone who reads the file can push to every repo you have access to. The passphrase is your second factor; `keychain` (Step 3) makes the day-to-day cost almost zero.

This creates two files:

- `~/.ssh/id_ed25519_codeberg` — the **private key** (never share, never commit)
- `~/.ssh/id_ed25519_codeberg.pub` — the **public key** (safe to share; goes to Codeberg)

## Step 2 — Add the public key to Codeberg

Print the public key:

```bash
cat ~/.ssh/id_ed25519_codeberg.pub
```

You'll see a single line that looks like:

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...long-base64-string... your.name@conduction.nl
```

That whole line is the public key. The three space-separated parts are:

| Part | Example | Meaning |
|---|---|---|
| Algorithm | `ssh-ed25519` | Key type. Always starts with `ssh-`. |
| Public key data | `AAAAC3Nz...` | Base64-encoded public component. |
| Comment | `your.name@conduction.nl` | Free-form identifier — usually your email so future-you knows which key this is. |

Optionally, copy it straight to the Windows clipboard from WSL:

```bash
cat ~/.ssh/id_ed25519_codeberg.pub | clip.exe
```

Then go to <https://codeberg.org/user/settings/keys> → **Add Key**:

| Field | Value |
|---|---|
| Key Name | Free-form label only you see, e.g. `WSL Ubuntu - SKIKK Laptop`. Doesn't have to match the comment in the key. |
| Content | Paste the **whole line** from `cat` (algorithm + key + comment). |

Click **Add Key**.

## Step 3 — Tell SSH to use this key for Codeberg

Append a host block to `~/.ssh/config` so the `codeberg.org` host always uses this specific key, regardless of how many other keys you have loaded:

```bash
cat >> ~/.ssh/config <<'EOF'

Host codeberg.org
  HostName codeberg.org
  User git
  IdentityFile ~/.ssh/id_ed25519_codeberg
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
```

`chmod 600` is **required** — SSH refuses to read a config file that other users could see, and silently falls back to defaults. Forgetting this is the most common cause of "I added my key but it still asks for a password."

> **Common mistake:** Pasting the `Host codeberg.org` block directly into the shell. The shell tries to run `Host` as a command and you get `Command 'Host' not found`. The block belongs *inside* the file, hence the `cat >> ... <<EOF` heredoc above.

## Step 4 — Verify SSH works

```bash
ssh -T git@codeberg.org
```

Expected output:

```
Hi there, <YourCodebergUsername>! You've successfully authenticated with the key named <Your Key Name>, but Forgejo does not provide shell access.
```

The "does not provide shell access" line is expected and correct — Codeberg only allows git operations over SSH, not interactive shell sessions.

If you instead see `Permission denied (publickey)`:

- Did you paste the **public** key (`.pub` file) to Codeberg, not the private one?
- Did you `chmod 600 ~/.ssh/config`?
- Try `ssh -vT git@codeberg.org` for verbose output and check which key file SSH actually offered.

## Step 5 — Set up keychain so the passphrase persists across shells

Without help, SSH asks for the passphrase **every time** you `git push`. `keychain` is the standard solution: it runs `ssh-agent` once per WSL boot, loads your key into it (passphrase prompt), and then every subsequent shell (including Claude Code's Bash tool) shares the unlocked agent.

Install:

```bash
sudo apt install -y keychain
```

Add to `~/.bashrc` (or `~/.zshrc`):

```bash
cat >> ~/.bashrc <<'EOF'

# Keep an ssh-agent alive across shells, with the Codeberg key loaded
eval $(keychain --eval --quiet --agents ssh ~/.ssh/id_ed25519_codeberg)
EOF
```

Open a new terminal — keychain prompts for the passphrase **once**. From then on, every shell on the same WSL instance inherits the loaded agent. Reboot WSL → prompted once again. That's the floor: a passphrase is real security, and reducing it below "once per WSL reboot" would require pinning the passphrase to disk somewhere, which defeats the point.

> If you do not want a passphrase prompt **ever** (single-user laptop, you accept the risk), regenerate the key with an empty passphrase: `ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519_codeberg`. Not recommended — the only protection against a leaked key file is then nothing.

Verify the key is loaded:

```bash
ssh-add -l
# Expected:
# 256 SHA256:... your.name@conduction.nl (ED25519)
```

## Step 6 — Install the `tea` CLI for PR/issue API operations

SSH covers the git protocol. Operations that aren't part of the git protocol — creating a PR, posting a comment, listing issues, applying labels — go through Codeberg's REST API. The `tea` CLI is Gitea's official CLI for this; think of it as `gh` for Codeberg.

Install (Linux/WSL amd64):

```bash
sudo wget -O /usr/local/bin/tea https://dl.gitea.com/tea/0.11.0/tea-0.11.0-linux-amd64
sudo chmod +x /usr/local/bin/tea
tea --version
```

Other platforms / latest releases: <https://gitea.com/gitea/tea/releases>.

## Step 7 — Create a Codeberg API token

The token is what `tea` uses to identify itself when calling the REST API. It is **separate** from your SSH key — SSH is for git over SSH, the token is for HTTPS API calls.

Go to <https://codeberg.org/user/settings/applications> → **Generate New Token**:

| Field | Value |
|---|---|
| Token Name | `tea-cli-<laptop>` or similar, so you can recognise + revoke it later |
| Expiration | 90 days is a good default; rotate every quarter |
| Scopes | See table below |

**Required scopes** (tick the **write** sub-checkbox where applicable):

| Scope | Why |
|---|---|
| `repository` | Push branches, create files via API, manage releases |
| `issue` | PRs share the issue API surface on Gitea — needed for comments, labels, assignees, reviews |
| `user` | Identify the authenticated user |
| `organization` | List `Conduction` org repos, manage team membership reads |

**Skip** these — they add risk without value for normal dev work:

| Scope | Reason to skip |
|---|---|
| `activitypub` | Federation between Gitea instances (Mastodon-style). Not used by Conduction. |
| `misc` | Marginal endpoints (`/version`, `/signing-key`). Not needed. |
| `package` | Gitea package registry. Not used by Conduction. |
| `admin` | Instance admin. Codeberg admins only. |
| `notification` | Optional — only tick `read` if you want a future skill to read your Codeberg notifications. |

Click **Generate Token**. **Copy it immediately** — Codeberg shows it once and never again.

## Step 8 — Tell `tea` about the token

```bash
tea login add --name codeberg --url https://codeberg.org --token <paste-token-here>
```

Verify:

```bash
tea login list
```

You should see one row with `NAME=codeberg`, `URL=https://codeberg.org`, `USER=<YourCodebergUsername>`.

The token is stored in `~/.config/tea/config.yml` from now on. Every `tea` invocation reuses it.

## Step 9 — Switch existing repo remotes to Codeberg

Repos cloned before the migration still point at GitHub. To switch one:

```bash
git -C /path/to/repo remote set-url origin git@codeberg.org:Conduction/<repo-name>.git
```

For a freshly-cloned repo, use the SSH URL from the start:

```bash
git clone git@codeberg.org:Conduction/<repo-name>.git
```

**Sanity check** for any repo whose remote you switched:

```bash
git -C /path/to/repo ls-remote --heads origin | head -3
```

If you see branch refs, the remote is correctly pointing at Codeberg and your SSH key works. If you see "Permission denied" or "repository not found", retrace Steps 1-5.

> **Heads-up for Hydra users:** The Hydra orchestrator and its cron scripts (`scripts/orchestrate.sh`, `scripts/cron-*.sh`, `scripts/hydra-supervisor.sh`) still assume GitHub for issue dispatch. If you switch the Hydra repo's `origin` to Codeberg, `git push` from inside those scripts goes to Codeberg, but `gh issue` calls still hit GitHub — a temporary split-brain. Hold off on switching `hydra` and `openregister` origins until Hydra has migrated to `tea`/Codeberg APIs. The other repos (`.github`, `openwoo-app-website`, app repos) are safe to switch immediately.

## Step 10 — Install the VS Code Gitea extension (optional but recommended)

VS Code's built-in source control panel already works with the SSH remote — you can commit, push, pull, branch, and resolve conflicts. What it doesn't show is Codeberg issues + PRs (the GitHub PR extension has no Codeberg equivalent).

The community extension that fills this gap:

- **Name**: Gitea
- **Publisher**: Gitea Authors (also a separate `Gitea-VSCode` by IJustDev — that one is a working fallback if the official extension misbehaves)
- **Install**: VS Code → Extensions → search "Gitea" → Install
- **Configure**: Settings (`Ctrl+,`) → search "gitea" → set `gitea.serverurl` to `https://codeberg.org` and paste your token from Step 7 into `gitea.token`

What it gives you:

- Issues + PRs sidebar (open from the source control activity bar)
- PR list with status badges
- Click-through to PR diffs in the editor

What it doesn't give you:

- Inline review-comment threads pinned to file:line (the GitHub PR extension does this; Codeberg/Gitea's API supports it but no extension implements it cleanly yet)
- Workflow run logs (the GitHub Actions extension's equivalent for Forgejo Actions does not exist)

For the missing pieces, Claude Code + `tea` + the REST API fills the gap from inside your terminal.

## How Claude Code uses this setup

Claude Code's Bash tool inherits your shell environment, including `SSH_AUTH_SOCK` from keychain and the `~/.config/tea/config.yml` token. That means:

- `git clone`, `fetch`, `push`, `pull` against Codeberg — **just works** as long as you've entered the keychain passphrase since the last WSL boot.
- `tea pulls create`, `tea pulls list`, `tea labels create`, etc. — **just works** because the token is already on disk.
- REST calls via `curl https://codeberg.org/api/v1/...` with `-H "Authorization: token $(tea login default-token)"` — **just works**.

The only edge case: if you launch Claude Code from a shell that **predates** the `keychain` line in `~/.bashrc` (or you've never entered the passphrase in this WSL boot yet), the agent has no key loaded and git operations will appear to hang on a silent passphrase prompt. Fix: in any shell, run `keychain ~/.ssh/id_ed25519_codeberg` once. New Claude Code sessions inherit it automatically.

Claude Code's safety hook may also block `git push` until you say one of the explicit phrases (`push my changes`, `push for me`, `commit and push`, `please git push`) in your message to it. That's a separate guardrail layered on top of authentication — auth determines *can*, the phrase determines *should*. Both must pass.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Permission denied (publickey)` on `ssh -T git@codeberg.org` | Public key not added to Codeberg, or wrong key file referenced in `~/.ssh/config` | Re-paste `~/.ssh/id_ed25519_codeberg.pub` at <https://codeberg.org/user/settings/keys>. Verify `IdentityFile` in `~/.ssh/config`. |
| SSH config block is being interpreted as shell commands (`Host: command not found`) | Pasted block into the shell instead of into `~/.ssh/config` | Use the `cat >> ~/.ssh/config <<'EOF'` heredoc from Step 3. |
| Every `git push` asks for the passphrase | `keychain` not installed or not added to `~/.bashrc` | Step 5. After editing `~/.bashrc`, **open a new terminal** — keychain only runs on shell start. |
| Claude Code's Bash hangs on `git push` and never returns | Claude Code's shell doesn't have `SSH_AUTH_SOCK` — the WSL session it launched from had no agent | Run `keychain ~/.ssh/id_ed25519_codeberg` in any shell on the same WSL instance. New Claude Code Bash calls pick up the agent automatically. |
| `tea pulls list` errors with `could not open a new TTY` | `tea` is asking for an interactive login selection because no default was set | Run `tea login default codeberg`. Or pass `--login codeberg` to every command. |
| `tea login add` succeeds but `tea pulls create` says "401 Unauthorized" | Token lacks `write:repository` or `write:issue` | Regenerate the token with the scopes from Step 7. `tea login delete codeberg && tea login add ...`. |
| Pushed a branch but no PR appears in the Codeberg UI | Branches and PRs are separate — pushing a branch never creates a PR by itself | Run `tea pulls create --base development --head <branch> --title "..." --description "..."` or open it via the web UI. |
| Claude Code refuses to `git push` even though SSH works | The safety hook requires an explicit authorisation phrase | Reply to Claude with "push my changes", "push for me", "commit and push", or "please git push". |

## Bidirectional / migration notes

The migration to Codeberg may reverse — Conduction's tooling is being kept **bidirectional**, not Codeberg-only:

- The same SSH key works on GitHub too — add the same `.pub` to <https://github.com/settings/keys> and your existing GitHub workflow keeps working unchanged.
- Skills that talk to git hosts (`create-pr`, `review-pr`, `report-out`, `opsx-*`) detect the platform from the git remote URL and dispatch to `tea` / `gh` / `glab` accordingly. No skill is Codeberg-only.
- If you ever need to switch a repo back to GitHub: `git remote set-url origin git@github.com:ConductionNL/<repo>.git` — reversible at any time.

## See also

- [Workstation Setup](./workstation-setup.md) — the broader new-machine guide; this doc plugs into the GitHub CLI / Codeberg CLI section
- [Global Claude settings](./global-claude-settings.md) — read-only Bash policy + write-approval hooks (the source of the `push my changes` phrase)
- [Codeberg user settings — Keys](https://codeberg.org/user/settings/keys)
- [Codeberg user settings — Applications](https://codeberg.org/user/settings/applications)
- [`tea` documentation](https://gitea.com/gitea/tea) — full command reference for the Gitea CLI
- [Codeberg API reference](https://codeberg.org/api/swagger) — Swagger UI for the REST API surface (for the operations `tea` does not yet wrap)
