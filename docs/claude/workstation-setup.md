# Workstation Setup

How to set up a new machine for Conduction development. The stack is **Windows + WSL2 + Docker Desktop + VS Code** — this guide covers everything needed to go from a fresh Windows install to a working development environment.

## Workstation Setup (Windows)

Our development environment runs on **Windows + WSL2 + Docker Desktop + VS Code**. Follow these steps on a fresh Windows machine.

### 1. Install WSL2

Open PowerShell as Administrator:

```powershell
wsl --install -d Ubuntu-24.04
```

Restart your machine when prompted. After reboot, Ubuntu will ask you to create a Linux username and password.

### 2. Install Docker Desktop

Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/).

After installation:
1. Open Docker Desktop > **Settings** > **Resources** > **WSL Integration**
2. Enable integration with your Ubuntu distro
3. Click **Apply & Restart**

Verify in WSL:
```bash
docker --version
docker compose version
```

### 3. Install VS Code

Download and install [Visual Studio Code](https://code.visualstudio.com/).

### 4. Install VS Code Extensions

Open VS Code and install these extensions (`Ctrl+Shift+X`):

**Required:**

| Extension        | ID                           | Purpose                                              |
| ---------------- | ---------------------------- | ---------------------------------------------------- |
| Claude Code      | anthropic.claude-code        | AI coding assistant — core to this setup             |
| WSL              | ms-vscode-remote.remote-wsl  | Connect VS Code to WSL (Windows side)                |
| Docker           | ms-azuretools.vscode-docker  | Dockerfile syntax, container management              |
| PHP Intelephense | bmewburn.vscode-intelephense | PHP autocompletion, type checking, go-to-definition  |
| Volar            | vue.volar                    | Vue 2/3 language support (templates, script, style)  |
| ESLint           | dbaeumer.vscode-eslint       | JavaScript/Vue linting                               |
| Python           | ms-python.python             | Python language support (for ExApp sidecar wrappers) |

**Recommended:**

| Extension           | ID                           | Purpose                                                        |
| ------------------- | ---------------------------- | -------------------------------------------------------------- |
| PowerShell          | ms-vscode.powershell         | PowerShell 7 scripting (`.ps1` files)                          |
| GitLens             | eamodio.gitlens              | Advanced Git history, blame, line annotations                  |
| GitHub Copilot Chat | github.copilot-chat          | AI pair programmer (requires Copilot license)                  |
| YAML                | redhat.vscode-yaml           | Syntax & validation for `docker-compose.yml` and OpenSpec YAML |
| GitHub Actions      | github.vscode-github-actions | View and validate CI/CD workflows                              |
| Makefile Tools      | ms-vscode.makefile-tools     | Makefile support (`make check-strict`)                         |
| Pylance             | ms-python.vscode-pylance     | Enhanced Python type checking and IntelliSense                 |

**Optional:**

| Extension     | ID                      | Purpose                                                                 |
| ------------- | ----------------------- | ----------------------------------------------------------------------- |
| Git Assistant | ivanhofer.git-assistant | Commit message suggestions + uncommitted changes warnings on branch switch |
| Rainbow CSV   | mechatroner.rainbow-csv | Color-coded CSV/TSV highlighting                                        |
| Live Preview  | ms-vscode.live-server   | Preview HTML files directly inside VS Code (right-click → Show Preview) |

Or install all required + recommended at once from the CLI (run inside WSL terminal):

```bash
code --install-extension anthropic.claude-code
code --install-extension ms-azuretools.vscode-docker
code --install-extension bmewburn.vscode-intelephense
code --install-extension vue.volar
code --install-extension dbaeumer.vscode-eslint
code --install-extension ms-python.python
code --install-extension ms-vscode.powershell
code --install-extension eamodio.gitlens
code --install-extension github.copilot-chat
code --install-extension redhat.vscode-yaml
code --install-extension github.vscode-github-actions
code --install-extension ms-vscode.makefile-tools
code --install-extension ms-python.vscode-pylance
```

> **Note:** `ms-vscode-remote.remote-wsl` must be installed on the **Windows side** of VS Code, not inside WSL. Install it from VS Code on Windows before connecting to WSL.

### 4a. Extension Setup After Installing

Most extensions work immediately after install, but a few need a small configuration step.

#### PHP Intelephense

Intelephense indexes your PHP files automatically on first open. No configuration needed for basic usage. A few tips:

- The free tier covers autocompletion, go-to-definition, and diagnostics — enough for Nextcloud app development.
- If VS Code shows duplicate PHP suggestions, disable the built-in PHP extension: `Ctrl+Shift+P` → **"Extensions: Disable (Workspace)"** → search **PHP** → disable `vscode.php-language-features`.
- Premium license (one-time purchase) adds rename, code folding, and type inference across files — optional.

#### GitLens vs. GitKraken

**GitLens** (VS Code extension) gives you inline blame, commit history, and file/line comparisons directly in the editor — no separate app needed.

**GitKraken** is a standalone GUI Git client with a visual branch graph, interactive rebase, and team features. It runs alongside GitLens (they don't conflict). Install it **inside WSL** so it runs natively against your Linux repos — this avoids path translation issues that occur when a Windows-installed GitKraken tries to open `\\wsl$\` paths:

```bash
wget https://release.gitkraken.com/linux/gitkraken-amd64.deb
sudo dpkg -i gitkraken-amd64.deb && rm gitkraken-amd64.deb
# Fix any missing dependencies:
sudo apt-get install -f
# Launch:
gitkraken &
```

> Requires **WSLg** (Windows 11 with WSL 2.0+) for the GUI window to appear. Run `wsl --version` in PowerShell to confirm — look for `WSLg version`.

### 5. Connect VS Code to WSL

1. Open VS Code
2. Press `Ctrl+Shift+P` > **"WSL: Connect to WSL"**
3. Choose your Ubuntu distro
4. VS Code will install its server component in WSL automatically

From here, all VS Code terminal work happens inside WSL.

### 6. Claude Code Authentication

After installing the Claude Code extension, authenticate:

1. Open the Claude Code panel in VS Code (sidebar icon)
2. Sign in with your Anthropic account
3. Or from the terminal: `claude auth login`

### 7. Configure Global Claude Settings

Before using Claude in this workspace, set up user-level permissions and a safety hook that restricts which shell commands Claude can run automatically.

See **[global-claude-settings.md](./global-claude-settings.md)** for the full guide, including copy-ready example files and a new-machine checklist.

Quick install:

```bash
mkdir -p ~/.claude/hooks
cp global-settings/settings.json ~/.claude/settings.json
cp global-settings/block-write-commands.sh ~/.claude/hooks/block-write-commands.sh
chmod +x ~/.claude/hooks/block-write-commands.sh
```

---

## Prerequisites (WSL)

Run these commands inside WSL (the VS Code terminal after connecting to WSL).

### Node.js (via nvm)

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 20
```

### PHP 8.1+ & Composer

```bash
sudo apt update
sudo apt install -y php8.1-cli php8.1-xml php8.1-mbstring php8.1-curl php8.1-zip unzip
curl -sS https://getcomposer.org/installer | php
sudo mv composer.phar /usr/local/bin/composer
```

### GitHub CLI

```bash
sudo apt install -y gh
gh auth login
```

### PHP Quality Tools (phpcs, phpmd, psalm, phpstan)

Run `composer install` once after cloning an app to install PHP dev dependencies locally:

```bash
composer install
```

For commands, see [Code Quality](./README.md#code-quality) in the Stage 4 section of the main README.

If `composer install` fails because `vendor/` is owned by root (common when Docker first creates it):

```bash
# Option 1 — fix vendor ownership (requires sudo password)
sudo chown -R $USER:$USER vendor/
composer install

# Option 2 — install phpcs globally (no sudo needed)
composer global require "squizlabs/php_codesniffer:^3.9"
~/.config/composer/vendor/bin/phpcs --standard=phpcs.xml
```

> **Important:** Use phpcs v3 (`^3.9`) — the CI uses v3. phpcs v4 is incompatible with the project's `phpcs.xml` config.

### Playwright Browsers

The Playwright MCP servers use the Playwright-managed Chromium binary. Install it once:

```bash
npx playwright install chromium
```

> If the MCP server reports a different revision is needed (e.g. after a `@playwright/mcp` update), run the install from the npx cache that the MCP server uses. You can find it at `~/.npm/_npx/` — look for the directory containing `@playwright/mcp`.

### OpenSpec CLI

Used by all `/opsx-*` commands for spec-driven development:

```bash
npm install -g @fission-ai/openspec
```

> **Do NOT run `openspec init`** in an existing Conduction project — it already has a customized `openspec/` directory with Conduction-specific schemas, shared specs, and project changes. Running `init` would overwrite them.

**OpenSpec documentation:**
- [Official site](https://openspec.dev/) — Getting started, concepts, customization
- [GitHub](https://github.com/Fission-AI/OpenSpec) — Source, issues, releases
- [npm](https://www.npmjs.com/package/@fission-ai/openspec) — Package info
- [Workflow docs](./workflow.md) — Our workspace-specific workflow

### Claude Code CLI (optional, for terminal use)

```bash
npm install -g @anthropic-ai/claude-code
```

### Ollama + Qwen (optional, local LLM)

For running Claude Code with a local Qwen model (privacy, cost reduction, offline use), see **[local-llm.md](./local-llm.md)**. That guide covers Ollama installation, model selection, performance benchmarks, the Qwen Code CLI, and the Double Dutch RAD workflow for pairing Claude (day shift) with Qwen (overnight batch jobs).

### Summary Checklist

```bash
# Verify everything is installed
node --version        # v20.x+
php --version         # 8.1+
composer --version    # 2.x
docker --version      # 24+
gh --version          # 2.x+
openspec --version    # 1.x
npx playwright --version  # 1.x
```

Your machine is ready. See [Getting Started](./getting-started.md) to complete your first spec-driven change.
