# Claude Code Developer Guide

Documentation for Conduction's spec-driven development workflow, combining OpenSpec, GitHub Issues, and Claude Code.

## Guides

### [Getting Started](./getting-started.md)
Step-by-step guide from installation to your first completed change. Start here if you're new to the workflow.

### [Workflow Overview](./workflow.md)
Architecture overview of the full system: how specs, GitHub Issues, and plan.json fit together. Includes the plan.json format and flow diagrams.

### [Command Reference](./commands.md)
Detailed reference for every skill — OpenSpec built-ins (`/opsx-new`, `/opsx-ff`, etc.) and custom Conduction skills (`/opsx-plan-to-issues`, `/opsx-apply-loop`, `/opsx-pipeline`). Includes expected output and usage tips.

### [Writing Specs](./writing-specs.md)
In-depth guide on writing effective specifications: RFC 2119 keywords, Gherkin scenarios, delta specs, shared spec references, task breakdown, and common mistakes to avoid.

### [Writing Skills](./writing-skills.md)
How to create and structure skills: folder layout (`templates/`, `references/`, `examples/`, `assets/`), SKILL.md format, naming conventions, common patterns, and the extraction threshold rule.

### [Writing ADRs](./writing-adrs.md)
How to write Architectural Decision Records: structure, format, when to create one, and how ADRs feed into the OpenSpec workflow.

### [Writing Docs](./writing-docs.md)
Guidelines for writing and maintaining documentation within a project: structure, tone, what to document, and how docs connect to the spec-driven workflow.

### [App Lifecycle](./app-lifecycle.md)
Creating and managing Nextcloud apps: design research (`/app-design`), bootstrapping from template or onboarding an existing repo (`/app-create`), thinking through goals and features (`/app-explore`), applying config to code (`/app-apply`), and auditing for drift (`/app-verify`). Includes `project.md` and `openspec/config.yaml` templates, and an onboarding checklist.

### [Docker Environment](./docker.md)
Available docker-compose profiles, reset instructions, and environment setup.

### [Global Claude settings (`~/.claude`)](./global-claude-settings.md)
**Mandatory** user-level settings enforcing a read-only Bash policy and write-approval hooks. Versioned — Claude warns you at session start when an update is available. Install once per machine; see the doc for the full guide and update instructions.

### [Testing Reference](./testing.md)
All testing commands and skills in one place — when to use each, typical workflows (pre-PR, regression sweep, smoke test), per-command "use when" guidance, test scenario integration, and browser pool rules.

### [Parallel Agents & Subscription Cap](./parallel-agents.md)
How parallel agent commands (like `/test-counsel`, `/test-app`, and `/feature-counsel`) consume your Claude subscription cap, guidelines for responsible use, and which files to keep lean to reduce token usage.

### [Frontend Standards](./frontend-standards.md)
Frontend development standards enforced across all Conduction apps: OpenRegister dependency checking, CSS scoping, admin detection patterns, and reference implementations.

### [Local LLM Setup (Ollama + Qwen)](./local-llm.md)
How to run Claude Code with a local Qwen model via Ollama for privacy, cost reduction, and offline use. Includes the Double Dutch RAD workflow for pairing Claude (day shift) with Qwen (overnight batch jobs).

### [Playwright MCP Browser Setup](./playwright-setup.md)
Detailed setup guide for the 7 independent Playwright browser sessions used for parallel testing, including VS Code extension configuration, CLI alternatives, and usage rules.

### [Usage Tracker](../../usage-tracker/README.md)
Real-time Claude token usage monitoring in VS Code — color-coded status, threshold notifications, and multi-model support (Haiku, Sonnet, Opus). Reads Claude Code session files directly; no log configuration needed. Run `bash usage-tracker/install.sh` to get started.

### [End-to-End Walkthrough](./walkthrough.md)
A complete worked example showing every phase of the flow on a realistic feature (adding a search endpoint to OpenCatalogi). Shows exactly what you type and what happens.

---

## Table of Contents

- [Work Pipeline](#work-pipeline)
  - [Stage 1: Obtain](#stage-1-obtain--discovery--requirements-gathering)
  - [Stage 2: Specify](#stage-2-specify--writing-openspec-artifacts)
  - [Stage 3: Build](#stage-3-build--configuration-not-code)
  - [Stage 4: Validate](#stage-4-validate--quality-assurance--verification)
- [Workstation Setup (Windows)](#workstation-setup-windows)
- [Prerequisites (WSL)](#prerequisites-wsl)
- [Local Configuration](#local-configuration)
- [Playwright MCP Browser Setup](#playwright-mcp-browser-setup)
- [Directory Structure](#directory-structure)
- [Personas](#personas)
- [Architectural Design Rules (ADRs)](#architectural-design-rules-adrs)
- [Usage Tracker](#usage-tracker)
- [Related: Hydra CI/CD Pipeline](#related-hydra-cicd-pipeline)
- [Scripts](#scripts)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)

---

## Work Pipeline

Claude follows a four-stage pipeline for all development work. Each stage has dedicated commands and tools. Claude operates as an **architect and orchestrator** — it defines, configures, and validates but delegates actual code generation to the platform's building blocks.

```mermaid
graph TD
    subgraph "1. OBTAIN"
        direction LR
        O1[GitHub Issues]
        O2[App Crawling]
        O3[Documentation]
        O4[Tenders / RFPs]
        O5[App Store Scouting]
    end

    subgraph "2. SPECIFY"
        direction TB
        S1[proposal.md]
        S2[specs.md]
        S3[design.md]
        S4[tasks.md]
        S5[GitHub Issues]
        S1 --> S2 --> S3 --> S4 --> S5
    end

    subgraph "3. BUILD"
        direction LR
        B1["Frontend<br/>@conduction/nextcloud-vue"]
        B2["Backend Data<br/>OpenRegister Schemas"]
        B3["Backend Logic<br/>n8n Workflows"]
    end

    subgraph "4. VALIDATE"
        direction TB
        V1["Code Quality<br/>PHPCS · PHPMD · Psalm"]
        V2["Testing<br/>API · Browser · Personas"]
        V3["CI/CD<br/>GitHub Actions"]
        V1 --> V2 --> V3
    end

    O1 & O2 & O3 & O4 & O5 --> S1
    S5 --> B1 & B2 & B3
    B1 & B2 & B3 --> V1

    style O1 fill:#e3f2fd,stroke:#1565c0
    style O2 fill:#e3f2fd,stroke:#1565c0
    style O3 fill:#e3f2fd,stroke:#1565c0
    style O4 fill:#e3f2fd,stroke:#1565c0
    style O5 fill:#e3f2fd,stroke:#1565c0
    style S1 fill:#fff3e0,stroke:#e65100
    style S2 fill:#fff3e0,stroke:#e65100
    style S3 fill:#fff3e0,stroke:#e65100
    style S4 fill:#fff3e0,stroke:#e65100
    style S5 fill:#fff3e0,stroke:#e65100
    style B1 fill:#e8f5e9,stroke:#2e7d32
    style B2 fill:#e8f5e9,stroke:#2e7d32
    style B3 fill:#e8f5e9,stroke:#2e7d32
    style V1 fill:#fce4ec,stroke:#c62828
    style V2 fill:#fce4ec,stroke:#c62828
    style V3 fill:#fce4ec,stroke:#c62828
```

**Key commands per stage:**

```mermaid
graph TD
    E["/opsx-explore"] --> N["/opsx-new"]
    N --> FF["/opsx-ff"]
    FF --> PI["/opsx-plan-to-issues"]
    PI --> A["/opsx-apply"]
    A --> V["/opsx-verify"]
    V --> TC["/test-counsel"]
    TC --> AR["/opsx-archive"]

    style E fill:#e3f2fd,stroke:#1565c0
    style N fill:#fff3e0,stroke:#e65100
    style FF fill:#fff3e0,stroke:#e65100
    style PI fill:#fff3e0,stroke:#e65100
    style A fill:#e8f5e9,stroke:#2e7d32
    style V fill:#fce4ec,stroke:#c62828
    style TC fill:#fce4ec,stroke:#c62828
    style AR fill:#fce4ec,stroke:#c62828
```

### Stage 1: Obtain — Discovery & Requirements Gathering

Collect requirements, study existing solutions, and identify what to build. Claude explores without making changes.

| Source | How | Commands / Tools |
|--------|-----|------------------|
| **GitHub issues** | Sync and analyze open issues from project repos | `/swc-update`, `gh issue list`, `gh issue view` |
| **Other applications** | Crawl code or browse running apps to understand patterns | `/opsx-explore`, Playwright browsers (`browser-1`–`browser-7`) |
| **Documentation** | Read docs from other platforms, APIs, standards | `WebFetch`, `WebSearch`, `/opsx-explore` |
| **Tenders** | Scrape TenderNed, classify by category, analyze requirements and ecosystem gaps | `/tender-scan`, `/tender-status`, `/tender-gap-report`, `/ecosystem-investigate`, `Read` (PDF support) |
| **App store scouting** | Spot interesting apps on WordPress plugin directory, GitHub trending, ArtifactHub, Nextcloud app store | `WebSearch`, `WebFetch`, Playwright browsers |

**Typical discovery session:**

```
/opsx-explore                              # Investigate a topic or problem
> "What calendar apps exist on ArtifactHub and WordPress that we could learn from?"
> "Crawl the Nextcloud app store for document management apps"
> "Analyze the GitHub issues for openregister and summarize themes"
```

### Stage 2: Specify — Writing OpenSpec Artifacts

Turn discoveries into structured specifications. This stage produces the blueprint that guides implementation.

| Phase | Artifact | Command |
|-------|----------|---------|
| **Start** | Change directory + `proposal.md` | `/opsx-new <change-name>` |
| **Proposal → Tasks** | All artifacts in one go (proposal, specs, design, tasks) | `/opsx-ff` |
| **Incremental** | One artifact at a time | `/opsx-continue` |
| **Review** | Multi-perspective feature analysis | `/feature-counsel` |
| **Architecture** | Architecture review of specs | `/team-architect` |
| **Business value** | Acceptance criteria and prioritization | `/team-po` |
| **New app** | Full app design from scratch (architecture, features, wireframes) | `/app-design` |
| **Track** | Convert tasks to GitHub Issues with epic | `/opsx-plan-to-issues` |

**Artifact progression:**

```
proposal.md ──► specs.md ──► design.md ──► tasks.md ──► plan.json
                                                          │
                                                          ▼
                                                    GitHub Issues
```

**Typical spec session:**

```
/opsx-new add-document-preview            # Start the change
/opsx-ff                                   # Generate all artifacts
/feature-counsel                           # Get 8-persona feedback
# Human reviews and refines specs
/opsx-plan-to-issues                       # Create trackable issues
```

### Stage 3: Build — Configuration, Not Code

Claude acts as an **assembler**, not a coder. It defines schemas, configures workflows, and wires up components using the platform's three pillars:

| Layer | Tool | Claude's Role |
|-------|------|---------------|
| **Frontend UI** | `@conduction/nextcloud-vue` | Select and configure components, define views and layouts, set up routing |
| **Backend data** | OpenRegister | Define schemas, registers, and object structures; configure validation rules and relations |
| **Backend logic** | n8n workflows | Design workflow logic, configure triggers, map data transformations |

Claude does **not** write raw PHP business logic, custom Vue components from scratch, or manual SQL. Instead:
- UI comes from the shared `@conduction/nextcloud-vue` component library
- Data models are OpenRegister schemas (JSON-based configuration)
- Business processes are n8n workflows (visual/JSON configuration)

| Command | Purpose |
|---------|---------|
| `/opsx-apply` | Implement tasks from the change — assembles components per the specs |
| `/opsx-sync` | Sync delta specs to main specs during implementation |

**Typical build session:**

```
/opsx-apply                                # Implement tasks from specs
# Claude configures schemas, wires components, sets up n8n flows
/opsx-sync                                 # Keep specs in sync
```

### Stage 4: Validate — Quality Assurance & Verification

Verify that the implementation matches the specs, passes quality standards, and works for all user types.

#### Code Quality

| Tool | Command | Checks |
|------|---------|--------|
| **PHPCS** | `composer phpcs` | Coding standards (auto-fix: `composer cs:fix`) |
| **PHPMD** | `composer phpmd` | Complexity, naming, unused code |
| **PHPStan** | `composer phpstan` | Static type analysis |
| **Psalm** | `composer psalm` | Type analysis (stricter) |
| **phpmetrics** | `composer phpmetrics` | Code metrics + violations |
| **ESLint** | `npm run lint` | JavaScript/Vue linting (auto-fix: `npm run lint -- --fix`) |
| **Stylelint** | `npm run stylelint` | CSS/SCSS linting |

> If `composer phpcs` fails due to a permissions error on `vendor/`, see [PHP Quality Tools setup](#php-quality-tools-phpcs-phpmd-psalm-phpstan) in Prerequisites.

#### Testing

For the full list of testing commands, browser pool rules, and recommended workflows, see [testing.md](./testing.md) and [commands.md](./commands.md).

Key commands: `/opsx-verify` (spec verification), `/test-counsel` (8-persona test sweep), `/test-app` (automated browser testing), `/test-functional`, `/test-api`, `/test-accessibility`, `/test-performance`, `/test-security`, `/test-regression`, and `/test-persona-*` (per-persona testing).

#### CI/CD

All apps have `code-quality.yml` GitHub Actions workflows that block PRs on:
- PHPCS + PHPMD + Psalm (PHP quality)
- ESLint (frontend quality)
- PHPUnit (unit tests)

#### Completion

| Command | Purpose |
|---------|---------|
| `/opsx-verify` | Final verification against specs — generates `review.md` |
| `/opsx-archive` | Archive the change, merge delta specs into main specs |
| `/opsx-bulk-archive` | Archive multiple completed changes at once |

**Typical validation session:**

```
composer phpcs && composer phpmd           # Code quality gates
/opsx-verify                               # Verify against specs
/test-counsel                              # 8-persona test sweep
/test-api                                  # API compliance check
/opsx-archive                              # Archive when everything passes
```

---

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

For commands, see [Code Quality](#code-quality) in the Stage 4 section above.

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

---

## Local Configuration

Claude Code uses three settings files that work together. Understanding the difference prevents confusion:

| File | Scope | Committed? | Purpose |
|------|-------|------------|---------|
| `~/.claude/settings.json` | Machine-wide, all projects | No — installed per developer | Global read-only policy and safety hooks. Installed from [`global-settings/`](../../global-settings/) in step 7 above. |
| `.claude/settings.json` | Project-wide, all developers | **Yes** | Shared team permissions — MCP server approvals, `enableAllProjectMcpServers`. Do not edit locally. |
| `.claude/settings.local.json` | Project, per developer | No — gitignored | Your personal tool approvals on top of the shared settings. Auto-generated by Claude Code. |

### settings.local.json

This file is **auto-generated** by Claude Code the first time you approve a tool permission in a session — no manual setup needed. It stores your personal allow/deny rules on top of the shared project settings.

Optionally, bootstrap it upfront with common permissions to avoid approval prompts during normal development:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "Bash(docker:*)",
      "Bash(docker-compose:*)",
      "Bash(composer:*)",
      "Bash(git:*)",
      "Bash(npm:*)",
      "Bash(php:*)",
      "Bash(curl:*)",
      "Bash(bash:*)",
      "Bash(ls:*)",
      "Bash(mkdir:*)",
      "Bash(cp:*)",
      "Bash(mv:*)",
      "Bash(rm:*)",
      "WebFetch(domain:localhost)",
      "WebFetch(domain:github.com)",
      "WebFetch(domain:raw.githubusercontent.com)"
    ],
    "additionalDirectories": [
      "/tmp"
    ]
  }
}
```

Save this as `.claude/settings.local.json` in your project root. It is gitignored and will never be committed.

### CLAUDE.local.md

Contains environment-specific credentials and API tokens (passwords, keys, endpoints). **Never commit this file.**

Copy the [example template](./examples/CLAUDE.local.md.example) into your project and fill in your values:

```bash
cp docs/claude/examples/CLAUDE.local.md.example .claude/CLAUDE.local.md
# Edit with your credentials
```

---

## Playwright MCP Browser Setup

The workspace uses 7 independent Playwright browser sessions for parallel testing. Copy the [example .mcp.json](./examples/.mcp.json.example) to your project root as `.mcp.json`, or see the [playwright-setup.md](./playwright-setup.md) guide for the full configuration, verification steps, CLI alternatives, and usage rules.

**Quick summary:**

| Server | Mode | Purpose |
|--------|------|---------|
| `browser-1` | Headless | Main agent (default) |
| `browser-2`–`browser-5`, `browser-7` | Headless | Sub-agent / parallel |
| `browser-6` | **Headed** | User observation (visible window) |

**Usage rules:** Use `browser-1` for normal work. Assign `browser-2`–`browser-5` and `browser-7` to parallel sub-agents. Keep `browser-6` reserved for user observation only.

---

## Directory Structure

### This repository (`.github`)

This repo contains **documentation**, **global settings**, and **project templates** — not skills, personas, or scripts. Those live in each project's own `.claude/` directory (see below).

```
.github/
├── docs/
│   └── claude/                       # Developer guides (this documentation)
│       ├── README.md                     # This file — overview and setup
│       ├── getting-started.md            # First-change walkthrough
│       ├── workflow.md                   # Spec-driven architecture reference
│       ├── commands.md                   # Full command reference
│       ├── testing.md                    # Testing commands and skills
│       ├── writing-specs.md              # How to write specs
│       ├── writing-skills.md             # How to create skills
│       ├── writing-adrs.md              # How to write ADRs
│       ├── writing-docs.md              # Documentation standards
│       ├── app-lifecycle.md             # Nextcloud app lifecycle
│       ├── frontend-standards.md        # Frontend coding standards
│       ├── parallel-agents.md           # Parallel agents and cap usage
│       ├── local-llm.md                 # Ollama + Qwen + Double Dutch
│       ├── playwright-setup.md          # Playwright browser configuration
│       ├── walkthrough.md               # End-to-end worked example
│       ├── docker.md                    # Docker environment
│       ├── global-claude-settings.md    # Global settings reference
│       └── examples/                    # Project-level template files
│           ├── CLAUDE.local.md.example      # Template for project .claude/CLAUDE.local.md
│           └── .mcp.json.example            # Template for project root .mcp.json (7 browsers)
│
├── global-settings/                  # Mandatory user-level settings for ~/.claude/
│   ├── settings.json                     # → ~/.claude/settings.json (global read-only policy)
│   ├── block-write-commands.sh           # → ~/.claude/hooks/block-write-commands.sh
│   ├── check-settings-version.sh         # → ~/.claude/hooks/check-settings-version.sh
│   └── VERSION                           # Version tracking for update checks
│
└── usage-tracker/                    # Claude token usage monitoring tool
```

### Typical project workspace

Each Conduction project (Nextcloud apps, WordPress sites, etc.) has its own `.claude/` directory with skills, personas, and configuration. The [Hydra](https://github.com/ConductionNL/hydra) repo also maintains its own set of skills and personas for CI/CD agents.

```
<project-root>/
├── .mcp.json                     # Playwright browser MCP servers (see docs/claude/examples/.mcp.json.example)
│
└── .claude/
    ├── CLAUDE.md                     # Workflow rules, project context
    ├── CLAUDE.local.md               # [GITIGNORED] Your credentials
    ├── CLAUDE.local.md.example       # Template — copy from global-settings/ or customize per project
    ├── settings.json                 # [COMMITTED] Shared team permissions
    ├── settings.local.json           # [GITIGNORED] Personal tool permissions (auto-generated)
    │
    ├── skills/                       # Project-specific skills (see commands.md)
    ├── personas/                     # User personas for testing
    ├── scripts/                      # Shared shell utilities
    └── docs/                         # Project-specific documentation
```

---

## Personas

Each project defines its own user personas in `personas/`. Personas drive multi-perspective analysis via `/feature-counsel` and testing via `/test-counsel`.

**Nextcloud workspace** — 8 Dutch government user personas representing public sector users:

| Persona | Age | Role | Perspective |
|---------|-----|------|-------------|
| Henk Bakker | 78 | Retired citizen | Accessibility, simple Dutch |
| Fatima El-Amrani | 52 | Low-literate migrant | Icons, mobile-first, B1 language |
| Sem de Jong | 22 | Digital native student | Performance, keyboard, dark mode |
| Noor Yilmaz | 36 | Municipal CISO | Security, BIO2, audit trails |
| Annemarie de Vries | 38 | VNG standards architect | GEMMA, NLGov API, interoperability |
| Mark Visser | 48 | MKB software vendor | CRUD efficiency, bulk operations |
| Priya Ganpat | 34 | ZZP developer | API quality, OpenAPI, DX |
| Jan-Willem van der Berg | 55 | Small business owner | Plain language, findability |

Other projects define personas relevant to their domain (e.g., the [wordpress-docker](https://github.com/ConductionNL/wordpress-docker) project uses shopper and admin personas). The [Hydra](https://github.com/ConductionNL/hydra) CI/CD pipeline also maintains its own copy of personas for automated testing.

---

## Architectural Design Rules (ADRs)

ADRs define constraints that all OpenSpec artifacts must comply with. Company-wide ADRs live in `openspec/architecture/`; app-specific ADRs live in `{app}/openspec/architecture/`. They are enforced at two points:

1. **During artifact creation** — `config.yaml` rules reference ADRs, which get injected into `openspec instructions` output
2. **During verification** — `/opsx-verify` checks ADR compliance as a report dimension

### Current ADRs

| ADR | Title | Enforced In |
|-----|-------|-------------|
| 001 | OpenRegister as Universal Data Layer | design: no custom DB tables |
| 002 | REST API Conventions | specs: URL patterns, error format |
| 003 | NL Design System for All UI | design: CSS variables only |
| 004 | Nextcloud App Framework Patterns | design: DI, annotations |
| 005 | i18n — Dutch and English Required | tasks: translation tasks |
| 006 | OpenRegister Schema Standards | specs: schema definitions |
| 007 | Security and Authentication | specs: auth requirements |
| 008 | Backend Layering (Controller -> Service -> Mapper) | design: layer structure |
| 009 | Mandatory Test Coverage (75%) | tasks: test tasks |
| 010 | Documentation with Screenshots | tasks: docs + Playwright screenshots |
| 011 | Deduplication Check Against OR Core | proposal: check existing features |
| 012 | Frontend Patterns (@conduction/nextcloud-vue) | design: component reuse |
| 013 | Loadable Register Templates | specs: register JSON format |
| 014 | Per-App Register Content i18n | specs: translatable fields |
| 015 | Per-App Prometheus Metrics | specs: metrics endpoints |
| 016 | Mandatory Seed Data for Testability | design: seed data section; tasks: seed data task |

### How ADRs Flow Into Work

```
config.yaml rules -> openspec instructions -> artifact content -> verify checks
```

ADRs are referenced in each app's `openspec/config.yaml` under the `rules:` section per artifact type. When an agent creates a proposal, design, spec, or task list, the CLI injects these rules into the instructions. The agent MUST follow them.

### Adding a New ADR

See [writing-adrs.md](./writing-adrs.md) for the full guide on structure, format, and when to create one.

Quick start:

1. Create `openspec/architecture/adr-NNN-title.md` (company-wide) or `{app}/openspec/architecture/adr-NNN-title.md` (app-specific) following the template in `openspec/architecture/README.md`
2. Add reference rules to `config.yaml` for the relevant artifact types
3. Update this table

---

## Usage Tracker

Monitor your Claude token usage in real-time to avoid hitting subscription limits mid-session. The tracker reads Claude Code's JSONL session files directly — no extra configuration needed.

```bash
# Install
bash usage-tracker/install.sh

# Quick status (all models)
python3 usage-tracker/claude-usage-tracker.py --status-bar --all-models

# Live monitoring (refreshes every 5 min)
python3 usage-tracker/claude-usage-tracker.py --monitor --all-models
```

See [usage-tracker/README.md](../../usage-tracker/README.md) for full documentation, VS Code task integration, and limit configuration.

---

## Related: Hydra CI/CD Pipeline

[Hydra](https://github.com/ConductionNL/hydra) is Conduction's agentic CI/CD platform that runs the same spec-driven workflow autonomously in Docker containers. It transforms OpenSpec change proposals into validated, security-scanned code on feature branches — with final human approval before merging.

Hydra maintains its own skills, personas, and OpenSpec workflows in its repository, running them through three specialized agent containers:

| Agent | Role | Permissions |
|-------|------|-------------|
| **Al Gorithm** (Builder) | Reads OpenSpec change, implements code, opens draft PR | Full: Read, Write, Edit, Bash |
| **Juan Claude van Damme** (Reviewer) | Code review for correctness, style, architecture | Read-only |
| **Clyde Barcode** (Security) | SAST analysis, secret detection, security hardening | Read-only |

The workflow and commands documented in this guide apply to both interactive development and Hydra's automated agents. See the [Hydra repository](https://github.com/ConductionNL/hydra) for container architecture, agent configuration, deployment models, and operational guides.

---

## Scripts

Each project may include shell scripts in its `.claude/scripts/` or `scripts/` directory, used by skills and developers. Common examples:

| Script | Description | Usage |
|--------|-------------|-------|
| `clean-env.sh` | Full Docker environment reset — stops containers, removes volumes, restarts, installs core apps | `bash scripts/clean-env.sh` or `/clean-env` |

---

## Contributing

### Adding a Skill

Skills are added to each project's `.claude/skills/` directory. See [writing-skills.md](./writing-skills.md) for the full guide on folder layout, SKILL.md format, naming conventions, maturity levels, and the extraction threshold rule.

Quick start:

1. Create `skills/<skill-name>/SKILL.md` in your project's `.claude/` directory
2. Use frontmatter:
   ```yaml
   ---
   name: skill-name
   description: What this skill does
   ---
   ```
3. Document instructions and expected behavior

### Adding a Persona

Personas are added to each project's `personas/` directory.

1. Create `personas/<firstname-lastname>.md`
2. Follow the existing format (see any existing persona file in the project)
3. Update skills that reference the persona list

### PR Process

1. Create a branch: `git checkout -b my-change`
2. Make changes, commit, push
3. Create PR against `main`

---

## Troubleshooting

### `openspec: command not found`

```bash
npm install -g @fission-ai/openspec
```

### Playwright browser not launching

```bash
npx playwright install chromium
# If permission errors:
npx playwright install --with-deps chromium
```

### MCP servers not showing in VS Code / not connected

1. Confirm `.mcp.json` exists in your **project root**
2. Confirm `settings.json` contains `"enableAllProjectMcpServers": true`
3. Reload the window: `Ctrl+Shift+P` → `reload window`
4. Check the output panel for errors: `Ctrl+Shift+P` → **"Output: Focus on Output"** → select **"Claude VSCode"**

You can verify the MCP binary itself starts correctly:

```bash
npx -y @playwright/mcp@latest --headless --isolated --port 9999
# Should print: Listening on http://localhost:9999
```

### Claude Code doesn't see commands

Ensure `.claude/` is at the workspace root and Claude Code is started from that directory.

### `gh: not logged in`

```bash
gh auth login
```

### Docker environment not starting

```bash
docker compose -f openregister/docker-compose.yml up -d
# Full reset:
/clean-env
```

### "You've hit your limit · resets 3pm (Europe/Amsterdam)"

This means you've reached your Claude subscription's usage cap. It can happen after running commands that launch many agents in parallel (`/test-counsel`, `/feature-counsel`, `/test-app` in Full mode).

See [parallel-agents.md](./parallel-agents.md) for an explanation of why parallel agents drain the cap, guidelines for careful use, and tips to reduce token usage (including always opening a fresh window before running these commands).

To monitor your usage proactively before hitting the limit, use the [usage tracker](../../usage-tracker/README.md):
```bash
python3 usage-tracker/claude-usage-tracker.py --status-bar --all-models
```
