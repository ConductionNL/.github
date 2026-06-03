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

## Step 11 — Optional: web-session cookies for PR thread resolution

**Skip this step unless you regularly do PR re-reviews on Codeberg.** It's a workaround for one specific gap in the Codeberg API; if you only push code and create PRs, the SSH key + `tea` token from Steps 1–8 are enough.

### What this is for

When you finish a re-review on a Codeberg PR and submit an APPROVE verdict, the inline-comment threads from your previous review stay open in the UI as unresolved "conversations" (Dutch: *Gesprekken*). On GitHub, the `/review-pr` skill closes these via the GraphQL `resolveReviewThread` mutation — but Codeberg's v1 REST API (`/api/v1/...`) has **no equivalent setter**. The `resolver` and `resolved_at` fields are exposed on `PullReviewComment` for reading but cannot be written.

The only way to programmatically click "Gesprek oplossen" / "Resolve conversation" on Codeberg is via the same web-form endpoint the browser uses (`POST /<owner>/<repo>/issues/resolve_conversation`), which requires the **browser session cookies**, not the API token. Treating those cookies like a password and storing them encrypted with your existing Codeberg SSH key lets Claude resolve threads programmatically without you re-extracting from the browser every time.

This is an alternative to manually clicking "Gesprek oplossen" on each thread. Pick this if either is true:

- You re-review more than two or three Codeberg PRs per week.
- You frequently have 5+ inline comments per re-review and the manual click-fest is painful.

### How it works

Four browser cookies authenticate the resolve endpoint (verified against Conduction/openregister on 2026-06-02):

| Cookie | Lifetime | Purpose |
|---|---|---|
| `cb_sessionid` | Browser session | Codeberg session ID (Codeberg-specific name — vanilla Forgejo uses `i_like_gitea`) |
| `persistent` | Weeks / months | "Remember me" token — this is what actually authenticates the request |
| `techaro.lol-anubis-auth` | ~7 days (see JWT `exp`) | Anubis anti-bot JWT — without it the request gets redirected to a challenge page |
| `x-robot-challenge-2` | Session | Secondary Anubis marker (literal value `passed`) |

The `/issues/resolve_conversation` route does **not** require a CSRF token despite being state-changing — cookies alone are sufficient. (Other Codeberg form endpoints do require CSRF; this one is the exception.)

The practical horizon is the Anubis JWT (~7 days). After it expires, calls start failing with `HTTP 302/303 → /user/login` and you re-extract from a fresh browser tab.

### Setup

1. **Install `age`** (modern file encryption, single binary):

   ```bash
   sudo apt install -y age
   ```

2. **Extract the four cookies from a logged-in Codeberg browser tab.** DevTools → **Application** (Chrome) or **Storage** (Firefox) → **Cookies** → `https://codeberg.org`. Copy the **Value** of each cookie above. Join them with `; ` into a single string:

   ```
   cb_sessionid=<v>; persistent=<v>; techaro.lol-anubis-auth=<v>; x-robot-challenge-2=passed
   ```

3. **Encrypt the cookie string to disk**, using your Codeberg SSH pubkey as the recipient so the same key that already secures `git push` also secures these cookies:

   ```bash
   age -R ~/.ssh/id_ed25519_codeberg.pub -o ~/.codeberg-cookies.age
   # paste the cookie string above, press Enter, then Ctrl-D
   chmod 600 ~/.codeberg-cookies.age
   ```

   The encrypted blob is ~800 bytes. Anyone reading the file without your SSH private key cannot decrypt it.

4. **Add three shell helpers to `~/.bashrc`**:

   ```bash
   cat >> ~/.bashrc <<'EOF'

   # ---- Codeberg web-session cookies (for resolve-conversation form posts) ----
   # Encrypted at ~/.codeberg-cookies.age via the Codeberg SSH pubkey.
   # Decryption prompts for the SSH passphrase once per terminal session.
   # See ~/.github/docs/claude/codeberg-auth-setup.md Step 11.

   cb-cookies-load() {
       if [ -n "$CB_COOKIES" ]; then
           echo "Codeberg cookies already loaded in this shell."
           return 0
       fi
       if [ ! -f ~/.codeberg-cookies.age ]; then
           echo "cb-cookies-load: ~/.codeberg-cookies.age not found." >&2
           echo "  Re-extract from a logged-in Codeberg browser tab and run cb-cookies-refresh." >&2
           return 1
       fi
       local out
       out="$(age -d -i ~/.ssh/id_ed25519_codeberg ~/.codeberg-cookies.age)" || return 1
       export CB_COOKIES="$out"
       echo "Codeberg cookies loaded into \$CB_COOKIES (this shell only)."
   }

   cb-cookies-refresh() {
       echo "Paste the full Codeberg cookie string (single line, semicolon-separated), then Enter:"
       local new
       IFS= read -rs new
       echo
       if [ -z "$new" ]; then
           echo "cb-cookies-refresh: empty input, aborted." >&2
           return 1
       fi
       printf '%s' "$new" | age -R ~/.ssh/id_ed25519_codeberg.pub -o ~/.codeberg-cookies.age || return 1
       chmod 600 ~/.codeberg-cookies.age
       unset new
       export CB_COOKIES=""
       echo "Codeberg cookies re-encrypted at ~/.codeberg-cookies.age. Run cb-cookies-load to use them."
   }

   cb-cookies-clear() {
       unset CB_COOKIES
       echo "Codeberg cookies cleared from this shell."
   }
   EOF
   ```

   Open a new terminal so `~/.bashrc` reloads.

### Daily use

```bash
cb-cookies-load    # once per terminal session (prompts for SSH passphrase)
# ... Claude or you can now POST to /issues/resolve_conversation with $CB_COOKIES ...
cb-cookies-clear   # when done, hygiene
```

The `/review-pr` skill detects `~/.codeberg-cookies.age` automatically and, on a Codeberg re-review, prompts you to run `cb-cookies-load` instead of re-pasting cookies each time.

### Refreshing when cookies expire (~7 days)

```bash
cb-cookies-refresh   # paste fresh cookie string from the browser, Enter
```

The function reads the new value with `IFS= read -rs` so the cookie string never appears on a command line, in process listings, or in shell history.

### Reading the Anubis JWT expiry (sanity check)

The `techaro.lol-anubis-auth` cookie is a JWT — decode it to know exactly when it expires:

```bash
python3 -c "
import base64, json, sys
jwt = sys.argv[1].split('.')[1]
print(json.loads(base64.urlsafe_b64decode(jwt + '==')))
" '<paste-jwt-here>'
```

Output includes `exp: <unix-timestamp>`; convert with `date -d @<ts>` to a human date.

### Why an existing SSH key instead of `gpg` or a fresh `age` identity?

- **`age` + SSH key** — re-uses the key you already have. The same `keychain`-unlocked passphrase that protects `git push` also protects the cookies. No new credential surface.
- `gpg` / `pass` — works fine but requires a GPG keyring you may not have set up.
- A fresh `age` identity (`age-keygen`) — adds another secret to store somewhere. Net loss of simplicity.

The trade-off with the SSH key route: `age` reads the key file directly and cannot tap the SSH agent, so each shell session prompts for the SSH passphrase once on first `cb-cookies-load`. That's the same pattern as `git push` over SSH and acceptable for a once-per-terminal cost.

## How Claude Code uses this setup

Claude Code's Bash tool inherits your shell environment, including `SSH_AUTH_SOCK` from keychain and the `~/.config/tea/config.yml` token. That means:

- `git clone`, `fetch`, `push`, `pull` against Codeberg — **just works** as long as you've entered the keychain passphrase since the last WSL boot.
- `tea` commands that don't prompt (e.g. `tea pulls list`, simple reads) — **just work** because the token is already on disk.
- REST calls via `curl https://codeberg.org/api/v1/...` with `-H "Authorization: token <TOKEN>"` — **just work** once Claude can read the token (see the Bash permission rule below).

### Edge case 1: stale `SSH_AUTH_SOCK` from an old Claude Code launch

Claude Code's *non-login non-interactive* Bash shells don't source `~/.bashrc` or `~/.profile`, so the `SSH_AUTH_SOCK` Claude inherits is whatever your shell environment had at Claude-launch time. If keychain's agent has since died (reboot) or the agent was replaced (running `eval $(ssh-agent)` manually in a sibling terminal), Claude's `git push` to Codeberg fails with `ssh_askpass: ... No such file` followed by `Permission denied (publickey)` — and there's no way to type the passphrase from Claude's TTY-less shell.

**Two recoveries**:

- **Sustainable**: close Claude Code, open a fresh terminal where `~/.bashrc` has run (you'll see "* ssh-agent / ssh-add ..." from keychain), then relaunch Claude Code. The new Claude inherits keychain's live `SSH_AUTH_SOCK`.
- **In-session, if relaunching is inconvenient**: source the keychain env file at the start of any single Bash command that needs SSH:

  ```bash
  . ~/.keychain/$(hostname)-sh && git push codeberg <branch>
  ```

  Keychain writes a stable `$HOME/.keychain/<HOSTNAME>-sh` file with the current `SSH_AUTH_SOCK` / `SSH_AGENT_PID` `export` lines. Sourcing it gives the current Bash command access to the live agent without restarting Claude.

### Edge case 2: `tea pulls create` cannot run from Claude Code

`tea` v0.11.0 uses [`huh`](https://github.com/charmbracelet/huh) for its final confirmation prompt. `huh` opens `/dev/tty` directly — it does **not** read stdin — so piped input (`yes | tea ...`), `setsid -w bash -c 'tea ... < /dev/zero'`, `--login codeberg` + all fields specified, and any other way of avoiding a real interactive operator all fail with:

```
huh: could not open a new TTY: open /dev/tty: no such device or address
```

`script -q -c 'tea ...' /tmp/log` *does* create a PTY, but tea then hangs because there's still no operator typing y/n at the prompt. There is no `--non-interactive`, `--yes`, or env-var override in tea v0.11.0. Until upstream adds one, you cannot run `tea pulls create` (or any other tea command that confirms) from Claude Code.

**Workaround — direct Codeberg REST API call**:

The Codeberg REST API has no such prompt. Claude can create PRs, post comments, edit labels, etc. directly via `curl` using the same token tea has on disk. One-time setup:

1. Add a Bash permission rule to your **global** `~/.claude/settings.json` so Claude can read the token. The auto-mode classifier blocks credential-file reads even when `Bash(cat:*)` is in the allow list — you need an explicit path rule:

   ```json
   {
     "permissions": {
       "allow": [
         "Bash(cat:*)",
         "Bash(cat:~/.config/tea/config.yml*)"
       ]
     }
   }
   ```

   The settings file is often `chattr +i`'d for safety; remove with `sudo chattr -i ~/.claude/settings.json`, edit, optionally re-apply with `sudo chattr +i ...` after.

2. Claude (and any team member's Claude) can now create PRs like this:

   ```bash
   TOKEN=$(grep -E "^\s*token:" ~/.config/tea/config.yml | head -1 | awk '{print $2}')
   curl -sL -X POST \
     -H "Content-Type: application/json" \
     -H "Authorization: token ${TOKEN}" \
     -d "$(jq -Rn '{
       head: "<branch>",
       base: "main",
       title: "<title>",
       body: "<markdown body>"
     }')" \
     "https://codeberg.org/api/v1/repos/Conduction/<repo>/pulls"
   ```

   HTTP `201` = created; the response JSON has `.html_url` pointing at the new PR. Sanitize any log echo with `sed 's/[a-f0-9]\{40\}/<TOKEN-REDACTED>/g'` to avoid leaking the token (or any 40-char hex like commit SHAs) in conversation history.

### Edge case 3: the explicit push-authorization phrase

Claude Code's safety hook may also block `git push` until you say one of the explicit phrases (`push my changes`, `push for me`, `commit and push`, `please git push`) in your message to it. That's a separate guardrail layered on top of authentication — auth determines *can*, the phrase determines *should*. Both must pass.

## Save your Codeberg setup facts to Claude memory

Once this guide is working on your machine, save the host-specific facts (key path, `~/.keychain/$(hostname)-sh` env-file location, `~/.ssh/config` host alias) to **global** user memory at `~/.claude/CLAUDE.md`, **not** to a per-project auto-memory directory under `~/.claude/projects/<slug>/memory/`. Codeberg auth applies to every repo you touch, so a project-scoped file only fires when Claude is working in that one repo and misses every other Codeberg session.

Rule of thumb:

- **Global (`~/.claude/CLAUDE.md`)** — per-user, cross-project facts: SSH key path, keychain env-file location, copy-paste preferences, the `tea` login name. Loaded on every session.
- **Project auto-memory (`~/.claude/projects/<slug>/memory/`)** — project-scoped facts: a repo's conventions, ongoing initiatives, recurring review nits in that codebase. Loaded only when Claude opens that repo.

Either way, memory entries should link back to this canonical doc so the troubleshooting table stays the single source of truth.

A ready-to-copy template for the Codeberg-auth section of `~/.claude/CLAUDE.md` lives in [example-claude-md-codeberg.md](./example-claude-md-codeberg.md). Copy that block once per machine and every future Claude Code session — in any repo — reaches the right fix in one step instead of re-diagnosing from scratch.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Permission denied (publickey)` on `ssh -T git@codeberg.org` | Public key not added to Codeberg, or wrong key file referenced in `~/.ssh/config` | Re-paste `~/.ssh/id_ed25519_codeberg.pub` at <https://codeberg.org/user/settings/keys>. Verify `IdentityFile` in `~/.ssh/config`. |
| SSH config block is being interpreted as shell commands (`Host: command not found`) | Pasted block into the shell instead of into `~/.ssh/config` | Use the `cat >> ~/.ssh/config <<'EOF'` heredoc from Step 3. |
| Every `git push` asks for the passphrase | `keychain` not installed or not added to `~/.bashrc` | Step 5. After editing `~/.bashrc`, **open a new terminal** — keychain only runs on shell start. |
| Claude Code's Bash hangs on `git push` and never returns | Claude Code's shell doesn't have `SSH_AUTH_SOCK` — the WSL session it launched from had no agent | Run `keychain ~/.ssh/id_ed25519_codeberg` in any shell on the same WSL instance. New Claude Code Bash calls pick up the agent automatically. |
| `tea pulls list` errors with `could not open a new TTY` and no default-login is set | `tea` is asking for an interactive login selection | Run `tea login default codeberg`, or pass `--login codeberg` to every command. |
| `tea pulls create` errors with `could not open a new TTY` even with `--login codeberg` + all fields specified | tea's final confirmation prompt uses `huh`, which opens `/dev/tty` directly — there is no `--yes` / `--non-interactive` flag in v0.11.0 | Use the direct REST API workaround in [Edge case 2 above](#edge-case-2-tea-pulls-create-cannot-run-from-claude-code) — `curl` to `POST /api/v1/repos/<owner>/<repo>/pulls` with the tea-stored token. Requires the `Bash(cat:~/.config/tea/config.yml*)` permission rule. |
| `tea login add` succeeds but `tea pulls create` says "401 Unauthorized" | Token lacks `write:repository` or `write:issue` | Regenerate the token with the scopes from Step 7. `tea login delete codeberg && tea login add ...`. |
| Pushed a branch but no PR appears in the Codeberg UI | Branches and PRs are separate — pushing a branch never creates a PR by itself | Run `tea pulls create --base development --head <branch> --title "..." --description "..."` or open it via the web UI. |
| Claude Code refuses to `git push` even though SSH works | The safety hook requires an explicit authorisation phrase | Reply to Claude with "push my changes", "push for me", "commit and push", or "please git push". |
| `cb-cookies-load` succeeds but Claude's `/issues/resolve_conversation` POSTs return `HTTP 302/303 → /user/login` | Anubis JWT (`techaro.lol-anubis-auth`) has expired (~7-day lifetime), or the browser session was logged out | Re-extract all four cookies from a fresh logged-in Codeberg browser tab, then `cb-cookies-refresh` and `cb-cookies-load` again. Step 11. |
| `age: failed to obtain passphrase: ... /dev/tty is not available` when running `cb-cookies-load` from a non-interactive shell | `age` reads the SSH key file directly and prompts for the passphrase via `/dev/tty`; it cannot use the `ssh-agent` | Run `cb-cookies-load` once in an interactive terminal *before* the non-interactive shell starts. The exported `$CB_COOKIES` is inherited by every child shell launched from there. |

## Bidirectional / migration notes

The migration to Codeberg may reverse — Conduction's tooling is being kept **bidirectional**, not Codeberg-only:

- The same SSH key works on GitHub too — add the same `.pub` to <https://github.com/settings/keys> and your existing GitHub workflow keeps working unchanged.
- Skills that talk to git hosts (`create-pr`, `review-pr`, `report-out`, `opsx-*`) detect the platform from the git remote URL and dispatch to `tea` / `gh` / `glab` accordingly. No skill is Codeberg-only.
- If you ever need to switch a repo back to GitHub: `git remote set-url origin git@github.com:ConductionNL/<repo>.git` — reversible at any time.

## See also

- [Example `~/.claude/CLAUDE.md` snippet](./example-claude-md-codeberg.md) — ready-to-copy Codeberg-auth section for your global Claude memory
- [Workstation Setup](./workstation-setup.md) — the broader new-machine guide; this doc plugs into the GitHub CLI / Codeberg CLI section
- [Global Claude settings](./global-claude-settings.md) — read-only Bash policy + write-approval hooks (the source of the `push my changes` phrase)
- [Codeberg user settings — Keys](https://codeberg.org/user/settings/keys)
- [Codeberg user settings — Applications](https://codeberg.org/user/settings/applications)
- [`tea` documentation](https://gitea.com/gitea/tea) — full command reference for the Gitea CLI
- [Codeberg API reference](https://codeberg.org/api/swagger) — Swagger UI for the REST API surface (for the operations `tea` does not yet wrap)
- [`age` documentation](https://github.com/FiloSottile/age) — modern file encryption; used in Step 11 to protect the Codeberg web-session cookies with your existing Codeberg SSH key
