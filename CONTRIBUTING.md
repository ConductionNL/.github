# Contributing to Conduction

Thank you for your interest in contributing! Conduction builds open-source components for digital government infrastructure. Every contribution — code, documentation, translation, issue report, or idea — helps us move toward our goal: ensuring every resident of the Netherlands automatically receives the government services they are entitled to.

This document applies to all repositories under the [ConductionNL](https://github.com/ConductionNL) organization.

---

## Code of Conduct

This project is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [info@conduction.nl](mailto:info@conduction.nl).

---

## Ways to Contribute

You don't need to write code to contribute:

| Contribution type | Where |
|---|---|
| 🐛 Report a bug | GitHub Issues |
| 💡 Suggest a feature | GitHub Issues |
| 📖 Improve documentation | PR to the relevant repo |
| 🌐 Translate content | PR to `.github` (docs site) |
| 🔍 Review a pull request | GitHub PR review |
| 💬 Answer questions | GitHub Discussions / Issues |
| 🔒 Report a security issue | See [SECURITY.md](SECURITY.md) |

---

## First-Time Contributors

New to open source or to Conduction? Look for issues labeled [`good first issue`](https://github.com/search?q=org%3AConductionNL+label%3A%22good+first+issue%22&type=issues) — these are scoped to be approachable without deep context.

If you're unsure where to start, open a discussion or leave a comment on an issue you're interested in. We'll help you get oriented.

---

## Reporting Bugs

Before filing a bug report, check existing issues — it may already be reported. When creating a report, include:

- A clear, descriptive title
- Exact steps to reproduce the problem
- Expected vs actual behavior
- Screenshots, logs, or error messages where relevant
- Version of the app and Nextcloud (if applicable)

**For security issues, do NOT open a public issue. See [SECURITY.md](SECURITY.md).**

---

## Suggesting Enhancements

Enhancement suggestions are tracked as GitHub Issues. Include:

- A clear, descriptive title
- The problem you are trying to solve (not just the solution)
- Current behavior vs desired behavior
- Why this would be useful to others

---

## Contributing Code

### External contributors (fork & PR)

1. Fork the repository
2. Create a branch from `development`: `git checkout -b feature/your-feature-name`
3. Make your changes and commit using [Conventional Commits](#commit-messages)
4. Sign off your commits (see [DCO](#developer-certificate-of-origin-dco))
5. Push to your fork and open a PR targeting the `development` branch
6. Wait for CI to pass and request a review

### Conduction team members (direct branch)

1. Create a branch from `development`: `feature/*`, `bugfix/*`
2. Open a PR to `development` when ready

### PR checklist

Before opening a PR:

- [ ] CI quality checks pass locally (`composer cs:check`, `composer phpstan`, `npm run lint`)
- [ ] New code has tests where applicable
- [ ] Documentation updated if behavior changes
- [ ] PR labeled with `major`, `minor`, or `patch` (controls version bump)
- [ ] DCO sign-off on all commits (`git commit -s`)

---

## Branch Model

All branches are protected via organization-wide rulesets. Direct pushes are not allowed. Every change flows through a pull request with peer review and CI.

```
feature/* ──┐
bugfix/*  ──┼──→ development ──→ beta ──→ main
hotfix/*  ──┘                    ↑
                                 └── (hotfix can target beta or main directly)
```

| Target | Allowed sources | Reviews required | CI required |
|---|---|---|---|
| `development` | `feature/*`, `bugfix/*` | 1 | Quality CI |
| `beta` | `development`, `hotfix/*` | 1 | Quality CI |
| `main` | `beta`, `hotfix/*` | 2 | Branch Protection CI |

All rulesets enforce: no force pushes, no branch deletion, stale reviews dismissed on new pushes, all threads resolved before merge.

---

## Quality Workflow

Every PR triggers automated quality checks. **All must pass before merge.**

### PHP

| Check | Tool |
|---|---|
| Syntax | `php -l` |
| Code style | PHPCS (PSR-12) |
| Static analysis | PHPStan (level 5) + Psalm |
| Mess detection | PHPMD |

### Frontend

| Check | Tool |
|---|---|
| JavaScript/Vue | ESLint |
| CSS/SCSS | Stylelint |

### Dependencies

- License compliance (npm + composer)
- Known vulnerability scan (npm audit + composer audit)

**Run locally:**

```bash
# PHP
composer cs:check
composer cs:fix
composer phpstan
composer psalm
composer phpmd

# Frontend
npm run lint
npx stylelint "src/**/*.{css,scss,vue}"
```

---

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add proactive service matching
fix: resolve null pointer in namespace parser
docs: update contributing guide
chore: upgrade PHPStan to v2
refactor: extract classifier into own class
```

- Use the **imperative mood** ("add" not "added")
- Keep the first line under 72 characters
- Reference issues with `Closes #123` in the body where applicable

---

## Developer Certificate of Origin (DCO)

All contributions must be signed off. This certifies that you wrote the code or have the right to submit it:

```bash
git commit -s -m "feat: your commit message"
```

This adds a `Signed-off-by: Your Name <your@email.com>` trailer. By signing off, you agree to the [Developer Certificate of Origin](https://developercertificate.org/).

If you forget, amend your last commit: `git commit --amend -s`

---

## Release Process

Releases are fully automated via GitHub Actions on merge to `beta` (nightly) or `main` (stable). Version numbers are calculated from PR labels:

| Label | Effect |
|---|---|
| `major` | `1.0.0` → `2.0.0` |
| `minor` | `1.0.0` → `1.1.0` |
| `patch` (default) | `1.0.0` → `1.0.1` |

See [Release Process documentation](https://docs.conduction.nl/docs/WayOfWork/release-process) for full details.

---

## Development Setup

1. Install PHP 8.1+ and Node.js 20+
2. Install Composer
3. Clone the repository (or your fork)
4. Run `composer install && npm install`
5. Configure your [Nextcloud development environment](https://github.com/ConductionNL/nextcloud-docker-dev)

---

## Documentation

Documentation source lives in `website/` (this repo) and is published to [docs.conduction.nl](https://docs.conduction.nl).

To contribute to the docs:
1. Edit the relevant Markdown files under `website/docs/`
2. For Dutch translations, edit the corresponding file under `website/i18n/nl/`
3. Test locally: `cd website && npm install && npm run start`

---

## Community

- [Common Ground Slack](https://commonground.nl)
- [LinkedIn](https://www.linkedin.com/company/conduction/)
- [GitHub Discussions](https://github.com/orgs/ConductionNL/discussions)

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (EUPL-1.2 unless stated otherwise in the repository).
