# Contributing to Conduction Nextcloud Apps

Thank you for considering contributing to our projects! It's people like you that make open source such a great community.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* Use a clear and descriptive title
* Describe the exact steps which reproduce the problem
* Provide specific examples to demonstrate the steps
* Describe the behavior you observed after following the steps
* Explain which behavior you expected to see instead and why
* Include screenshots if possible

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* Use a clear and descriptive title
* Provide a step-by-step description of the suggested enhancement
* Describe the current behavior and explain which behavior you expected to see instead
* Explain why this enhancement would be useful

### Pull Requests

* Fork the repo and create your branch from `development`
* If you've added code that should be tested, add tests
* If you've changed APIs, update the documentation
* Ensure the test suite passes
* Make sure your code lints (`composer cs:check`)
* Create a pull request!

## Development Process

1. Create a feature request issue describing your proposed changes
2. Fork the repository
3. Create a new branch: `git checkout -b feature/[issue-number]/[feature-name]`
4. Make your changes
5. Run quality checks: `composer cs:check` and `composer phpstan`
6. Push to your fork and open a Pull Request

### Git Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

* `feat:` for new features
* `fix:` for bug fixes
* `chore:` for maintenance tasks
* `docs:` for documentation changes
* `refactor:` for code refactoring
* Use the present tense and imperative mood
* Limit the first line to 72 characters

### PR Labels for Changelogs

Add labels to categorize your PR in the automated changelog:

* **`feature`** / **`enhancement`** — New features (appears under "Added")
* **`bug`** / **`fix`** — Bug fixes (appears under "Fixed")
* **`docs`** — Documentation updates
* **`refactor`** / **`chore`** — Code improvements (appears under "Changed")
* **`skip-changelog`** — Exclude from changelog

## Development Setup

1. Install PHP 8.1+ and Node.js 20+
2. Install Composer
3. Clone the repository
4. Run `composer install` and `npm install`
5. Configure your [Nextcloud development environment](https://github.com/ConductionNL/nextcloud-docker-dev)

## Community

* Join the [Common Ground Slack](https://commonground.nl)
* Follow us on [X](https://x.com/conduction_nl)
* Read our updates on [LinkedIn](https://www.linkedin.com/company/conduction/)

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (EUPL-1.2 unless stated otherwise).
