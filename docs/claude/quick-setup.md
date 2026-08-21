# Quick Setup — for people who already know the system

A condensed setup recipe for developers who have done this before and just need the commands in order on a fresh machine. **Not for first-timers** — if this is your first Conduction workstation, follow the [Workstation Tutorial series](https://conduction.nl/academy/?series=workstation-tutorial) (one evening, six short modules, with screenshots) and use [`workstation-setup.md`](./workstation-setup.md) as the reference.

The canonical reference is [`workstation-setup.md`](./workstation-setup.md). This page is a shortcut, not a replacement.

## When to use this page

- You're re-imaging a known-good setup on a fresh laptop, WSL distro, or VM.
- You're onboarding to a second machine and already know the choices behind the stack.
- You're helping a colleague who needs the literal command sequence, not the rationale.

If any step surprises you, stop and read the corresponding section of [`workstation-setup.md`](./workstation-setup.md) — that doc explains *why* each tool is on the list.

## 1. Prerequisites (before anything Conduction-specific)

OS-level pieces that must exist before any command below works. For each row, **pick one** column — the three paths are equally supported, just different starting points:

| Component | Path A: Windows + WSL | Path B: Native Linux | Path C: macOS |
|---|---|---|---|
| **OS** | Windows 11 + WSL2 + Ubuntu 24.04 — `wsl --install -d Ubuntu-24.04` from elevated PowerShell, reboot, create Linux user | Ubuntu 24.04 (or comparable Debian-based distro) installed directly on the machine | macOS 13 Ventura or newer (Apple Silicon or Intel) with [Homebrew](https://brew.sh/) installed |
| **Docker** | Docker Desktop for Windows with WSL integration enabled for your Ubuntu distro | Docker Engine + Compose plugin natively: `sudo apt install -y docker.io docker-compose-plugin && sudo usermod -aG docker $USER` (logout/login) | Docker Desktop for Mac, **or** a lighter alternative like [OrbStack](https://orbstack.dev/) / [Colima](https://github.com/abiosoft/colima) |
| **Editor** | VS Code on Windows + the Remote-WSL extension (so the editor runs on Windows but the terminal + code live in Linux) | VS Code natively, **or** JetBrains PhpStorm / IntelliJ IDEA with the Claude Code plugin — pick whichever you already use | VS Code, **or** JetBrains PhpStorm / IntelliJ IDEA with the Claude Code plugin — pick whichever you already use |

Regardless of which path you take, you also need:

- A **Codeberg account** (`codeberg.org`) with repo access — ask your team lead for `Conduction/hydra` and any app repos you'll touch.
- A **Claude Max** account (OAuth, no API key needed for normal work).

The canonical [`workstation-setup.md`](./workstation-setup.md) documents the Windows + WSL2 path in most detail; the Linux and macOS paths reuse the same tools, just installed via `apt` or `brew` instead.

## 2. Which repos to clone

Two layers — pick what you need, skip the rest:

**Always:**

```bash
# The org repo with docs, global Claude settings, and shared tooling
git clone git@github.com:ConductionNL/.github.git ~/.github
```

**If you'll work on a Conduction Nextcloud app** (most developers):

```bash
git clone https://github.com/nextcloud/nextcloud-docker-dev.git ~/nextcloud-docker-dev
cd ~/nextcloud-docker-dev/apps-extra
git clone git@github.com:ConductionNL/openregister.git
git clone git@github.com:ConductionNL/integriq.git
# Add other app repos as needed (opencatalogi, filinq, …)
```

**If you'll work on Hydra itself** (the pipeline, not the apps it builds):

```bash
cd ~/nextcloud-docker-dev/apps-extra   # workspace layout per getting-started.md
git clone git@github.com:ConductionNL/hydra.git
```

> **Hydra vs .github — quick reminder.** `.github` is *the manual* (docs, way-of-work, global settings, public Hydra one-pager). `hydra` is *the factory* (containers, agent personas, orchestration scripts, the `.claude/skills/` catalogue). See [`docs/hydra/README.md`](../hydra/README.md#hydra-repo-vs-github-repo) for the full breakdown.

## 3. Commands in order

Run inside WSL Ubuntu (Path A) or your native Linux shell (Path B). Lines that need `sudo` say so explicitly.

> **macOS users (Path C):** the steps below are Linux/WSL-shaped. Map them to `brew` equivalents — most tools have a one-liner:
> `brew install nvm php composer gh && brew install --cask docker` (or use OrbStack instead of the Docker cask), `brew install gitea/tap/tea`. `npm install -g …` and `npx playwright install chromium` work unchanged once Node is installed. The `sudo chattr +i` lock in §3.7 is Linux-only; macOS users can use `sudo chflags uchg <file>` as the equivalent immutable bit. The rest of the command structure carries over one-to-one.

```bash
# --- 3.1 Node 20 via nvm ---
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
exec $SHELL
nvm install 20 && nvm use 20 && nvm alias default 20

# --- 3.2 PHP 8.1 + Composer ---
sudo apt update && sudo apt install -y php8.1-cli php8.1-curl php8.1-mbstring php8.1-xml php8.1-zip php8.1-sqlite3 composer

# --- 3.3 Git-host CLIs (tea = primary, gh = fallback) ---
# tea (Codeberg/Gitea/Forgejo)
sudo wget -O /usr/local/bin/tea https://dl.gitea.com/tea/0.11.0/tea-0.11.0-linux-amd64
sudo chmod +x /usr/local/bin/tea
# Token from https://codeberg.org/user/settings/applications
#   scopes: read:repository, write:repository, read:issue, write:issue
tea login add --name codeberg --url https://codeberg.org --token <YOUR_TOKEN>
# gh (GitHub fallback)
sudo apt install -y gh
gh auth login

# --- 3.4 Codeberg SSH key ---
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_codeberg -C "<your@email>"
# Paste ~/.ssh/id_ed25519_codeberg.pub at https://codeberg.org/user/settings/keys
# Then add to ~/.ssh/config:
#   Host codeberg.org
#       HostName codeberg.org
#       User git
#       IdentityFile ~/.ssh/id_ed25519_codeberg
#       IdentitiesOnly yes
sudo apt install -y keychain
keychain ~/.ssh/id_ed25519_codeberg

# --- 3.5 OpenSpec CLI + Claude Code CLI ---
npm install -g @fission-ai/openspec @anthropic-ai/claude-code
# DO NOT run `openspec init` inside an existing Conduction project — it overwrites the schema.

# --- 3.6 Playwright browser ---
npx playwright install chromium

# --- 3.7 Global Claude settings (mandatory) ---
# Cloned in step 2 to ~/.github
cd ~/.github
# Follow the install block in global-settings/README.md — copies settings.json + hooks
# to ~/.claude/, applies chattr +i for the kernel-level lock.
less global-settings/README.md      # then copy-paste the install block
```

For step 3.7's full install block (it includes a `sudo chattr +i` step that's easier to copy-paste from the README than transcribe here), see [`global-settings/README.md`](../../global-settings/README.md#install). Restart Claude Code after installing.

## 4. Validation

If all of the following succeed, your workstation is ready:

```bash
# Tooling versions
node --version                       # v20.x+
php --version                        # 8.1+
composer --version                   # 2.x
docker --version                     # 24+
docker compose version               # plugin present
tea --version                        # 0.10+
gh --version                         # 2.x+
openspec --version                   # 1.x
npx playwright --version             # 1.x

# Git-host auth
ssh -T git@codeberg.org              # → "Hi there, <YourCodebergUsername>!"
tea logins list                      # codeberg entry shown
gh auth status                       # logged in

# Claude global settings active
ls -l ~/.claude/settings.json        # exists, immutable bit will show via lsattr
lsattr ~/.claude/settings.json       # leading 'i' = immutable lock applied

# Nextcloud locally (if you cloned nextcloud-docker-dev)
cd ~/nextcloud-docker-dev && docker compose up -d nextcloud proxy
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080   # → 200 (or 302)
```

If any line fails, the corresponding section in [`workstation-setup.md`](./workstation-setup.md) has the full background and troubleshooting.

## What this page does *not* cover

- Detailed VS Code extension list — see [`workstation-setup.md` §4](./workstation-setup.md#4-install-vs-code-extensions).
- Onboarding flow, buddy system, ISO compliance — see [`docs/WayOfWork/onboarding.mdx`](../WayOfWork/onboarding.mdx).
- The Codeberg auth deep-dive (when `tea` parity gaps bite, when to use REST instead) — see [`codeberg-auth-setup.md`](./codeberg-auth-setup.md).
- Local LLM (Ollama + Qwen) for overnight batch jobs — see [`local-llm.md`](./local-llm.md).
- An automated bootstrap script — not yet. The command list above is the cheat-sheet for now; a `bootstrap-workstation.sh` may follow once the recipe has been validated on more clean WSL installs.
