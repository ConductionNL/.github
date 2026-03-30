---
id: contributing
title: Contributing to Conduction
sidebar_label: Contributing
sidebar_position: 6
description: How to contribute to Conduction's open-source projects — code, docs, translations, and more
---

# Contributing to Conduction

Thank you for your interest in contributing! Every contribution — code, documentation, translation, issue report, or idea — helps us move toward our goal: ensuring every resident of the Netherlands automatically receives the government services they are entitled to.

This guide applies to all repositories under [ConductionNL](https://github.com/ConductionNL). The authoritative source is [CONTRIBUTING.md](https://github.com/ConductionNL/.github/blob/main/CONTRIBUTING.md) in our organization `.github` repository.

---

## Ways to Contribute

You don't need to write code to contribute:

| Contribution type | Where |
|---|---|
| 🐛 Report a bug | GitHub Issues |
| 💡 Suggest a feature | GitHub Issues |
| 📖 Improve documentation | PR to the relevant repo |
| 🌐 Translate content | PR to `.github` (this docs site) |
| 🔍 Review a pull request | GitHub PR review |
| 💬 Answer questions | GitHub Discussions / Issues |
| 🔒 Report a security issue | See [Security Policy](../ISO/security) |

---

## First-Time Contributors

New to open source or to Conduction? Look for issues labeled [`good first issue`](https://github.com/search?q=org%3AConductionNL+label%3A%22good+first+issue%22&type=issues) — these are scoped to be approachable without deep context.

If you're unsure where to start, leave a comment on an issue you're interested in. We'll help you get oriented.

---

## Contributing Code

### External contributors (fork & PR)

1. Fork the repository
2. Create a branch from `development`: `git checkout -b feature/your-feature-name`
3. Make your changes and commit using [Conventional Commits](#commit-messages)
4. Sign off your commits (see [DCO](#developer-certificate-of-origin))
5. Push to your fork and open a PR targeting `development`

### Conduction team members (direct branch)

1. Create a branch from `development`: `feature/*` or `bugfix/*`
2. Open a PR to `development` when ready

### PR checklist

- [ ] CI quality checks pass locally
- [ ] New code has tests where applicable
- [ ] Documentation updated if behavior changes
- [ ] PR labeled with `major`, `minor`, or `patch`
- [ ] DCO sign-off on all commits (`git commit -s`)

---

## Branch Model

```
feature/* ──┐
bugfix/*  ──┼──→ development ──→ beta ──→ main
hotfix/*  ──┘
```

| Target | Allowed sources | Reviews required |
|---|---|---|
| `development` | `feature/*`, `bugfix/*` | 1 |
| `beta` | `development`, `hotfix/*` | 1 |
| `main` | `beta`, `hotfix/*` | 2 |

No force pushes. No direct pushes. All changes via pull request. See the full [Release Process](release-process) for details.

---

## Quality Workflow

Every PR triggers automated quality checks — all must pass before merge.

**PHP:** syntax lint, PHPCS (PSR-12), PHPStan (level 5), Psalm, PHPMD

**Frontend:** ESLint, Stylelint

**Dependencies:** license compliance, vulnerability scan

```bash
# Run locally
composer cs:check && composer phpstan && composer psalm
npm run lint
```

---

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add proactive service matching
fix: resolve null pointer in namespace parser
docs: update contributing guide
chore: upgrade PHPStan to v2
```

- Imperative mood ("add" not "added")
- First line under 72 characters
- Reference issues with `Closes #123` in the body

---

## Developer Certificate of Origin

All contributions must be signed off:

```bash
git commit -s -m "feat: your commit message"
```

This adds `Signed-off-by: Your Name <email>` and certifies you have the right to submit the contribution under the project license. See [developercertificate.org](https://developercertificate.org/).

---

## Development Setup

1. Install PHP 8.1+ and Node.js 20+
2. Install Composer
3. Clone the repository (or your fork)
4. Run `composer install && npm install`
5. Set up a [Nextcloud dev environment](https://github.com/ConductionNL/nextcloud-docker-dev)

---

## Community

- [Common Ground Slack](https://commonground.nl)
- [LinkedIn](https://www.linkedin.com/company/conduction/)
- [GitHub Discussions](https://github.com/orgs/ConductionNL/discussions)

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (EUPL-1.2 unless stated otherwise).
