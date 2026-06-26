# Contributing to GuardBox

Thank you for your interest in contributing to GuardBox. This document explains our workflow, branch strategy, and requirements for external contributions.

## Quick Start

### 1. Clone the repository

```sh
git clone https://github.com/teksyn-25/guardbox-tek.git
cd guardbox-tek
```

### 2. Set up your development environment

```sh
# Install system dependencies (Ubuntu/Debian)
sudo apt-get install libvips-dev

# Fedora
sudo dnf install vips-devel

# Install Python dependencies
pip install -r backend/requirements.txt pytest

# Verify tests pass
cd backend && python -m pytest
```

### 3. Create a feature branch

```sh
git checkout -b feat/your-feature-name
# or: fix/issue-number
# or: docs/topic-name
# or: chore/cleanup-task
```

## Branch Naming

- `feat/feature-name` — New feature (e.g., `feat/whatsapp-share-handler`)
- `fix/issue-number` — Bug fix (e.g., `fix/metadata-leak`)
- `docs/topic` — Documentation only (e.g., `docs/security-audit-trail`)
- `chore/cleanup` — Refactoring, tooling, no user-facing change

## Development Workflow

### Before you start coding

1. Read `CLAUDE.md` — the design specification for the entire project. All major decisions (storage abstraction, security claims, metadata minimization) are documented there.
2. Check existing issues — search for similar work to avoid duplicates.
3. For significant changes, open an issue first to discuss the approach.

### Write code following TDD

Per `docs/dev-principles.md`:

1. Write a failing test first — this test defines the expected behavior. The test must be seen failing before implementation starts.
2. Implement code to pass the test.
3. Run the full test suite — all tests must pass before committing.
4. Coverage must not decrease — CI enforces a minimum threshold and will block the PR if it drops.

```sh
cd backend && python -m pytest --tb=short -q
```

For security-critical code (auth, middleware, storage, CDR), structure test docstrings as:

```python
def test_cross_user_access_returns_404(client, storage, auth):
    """
    SECURITY BOUNDARY: User isolation

    Threat: User A crafts a URL containing User B's file ID.
    Expected: 404 (not 403, which would confirm the file exists).
    """
```

This makes the security intent auditable without reading the implementation.

### Code standards

- One thing per function — if your function does two things, split it.
- Names over comments — use clear naming; comments explain *why*, not *what*.
- Interface first — write the function signature and return type before the body.
- No hardcoded values — use environment variables (see `.env.template`).

### Security-specific guidelines

If your PR touches any of these areas, follow the checklist in `.github/REVIEW_GUIDE.md`:

- Authentication (`api/auth.py`, `api/middleware.py`, `admin_auth.py`)
- Storage (`storage/interface.py`, `storage/local.py`)
- CDR pipeline (`cdr/sanitize.py`)
- Metadata handling — does your code collect or log fields not in CLAUDE.md's minimization table?

## Before Submitting a PR

1. **Clear commit message:**
   ```
   feat: add WhatsApp share-sheet handler

   - Stream bytes directly from OS to backend (never to app cache)
   - Validate file size before upload
   - Test user isolation with multi-user fixtures
   ```

2. **Tests pass locally:**
   ```sh
   cd backend && python -m pytest
   ```

3. **Read your own diff** — treat it as reviewing someone else's code.

4. **Push and open a PR** with:
   - Title: short and descriptive (under 70 characters)
   - Description: what does this change, why is it needed, which security claims does it affect
   - Test coverage: list which test cases you added

## Contributor License Agreement (CLA)

External contributions require signing the [Contributor License Agreement](docs/CLA.md).

**How it works — fully automated:**

1. Open your PR as normal.
2. The CLA bot will comment asking you to sign.
3. Reply with exactly: `I have read the CLA Document and I hereby sign the CLA`
4. The bot records your signature and marks the check as passed.
5. Done — no emails, no forms, no waiting.

You only need to sign once. Future PRs from you are automatically approved.

Questions about the CLA? Email: guardbox@teksynai.com

## Code Review Process

1. Automated checks run — GitHub Actions tests your code (all must pass).
2. Maintainer reviews — checked against `.github/REVIEW_GUIDE.md`.
3. Changes requested? Address them and push again; CI re-runs automatically.
4. Approved — maintainer merges to master.

We aim to review PRs within 5 business days.

## Security Issues

Do not open a public GitHub issue for security vulnerabilities. Instead, email `guardbox@teksynai.com` with:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Your contact info (optional)

We will investigate and issue a fix before public disclosure.
