# SmartReply Clone CI/CD Configuration

## Overview
This repository uses GitHub Actions for continuous integration and deployment with security-first approach.

## Workflows

### 1. Main CI/CD Pipeline (`ci.yml`)
- **Triggers**: Push to `main`/`developer` branches, PRs to `main`
- **Features**:
  - Python 3.12 environment with `uv` package manager
  - Code quality checks (linting, formatting, type checking)
  - Security scanning with Bandit
  - Dependency vulnerability checks with Safety
  - Application validation and build
  - Automated deployment to production on main branch pushes

### 2. Security & Quality Gates (`security.yml`)
- **Triggers**: Push to `main` branch, PRs to `main`
- **Features**:
  - Enhanced security scanning
  - Branch protection validation
  - Environment validation
  - Production readiness checks

## Security Features

### Code Quality
- **Ruff**: Fast Python linter and formatter
- **MyPy**: Static type checking
- **Bandit**: Security vulnerability scanner
- **Safety**: Dependency vulnerability checker

### Branch Protection
- Main branch pushes require all checks to pass
- Environment validation before deployment
- Security reports generated and stored as artifacts

### Deployment Security
- Production environment protection
- Artifact validation before deployment
- Deployment notifications and logging

## Environment Variables Required
- `META_API_TOKEN`: Facebook Meta API verification token

## Usage
1. Push to `developer` branch for testing
2. Create PR to `main` for review
3. Merge to `main` triggers automatic deployment
4. All security and quality checks must pass

## Artifacts Generated
- Security scan reports (Bandit, Safety)
- Build artifacts for deployment
- Quality gate reports
