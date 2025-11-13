## CI/CD

GitHub Actions (`.github/workflows/ci-cd.yml`) runs for every push and pull request targeting `developer` or `main`:

- `Build & Test` checks out the repo, sets up Python 3.12, installs `requirements.txt`, and runs `pytest` if test files exist.
- `Deploy to VPS` runs only on push events to `developer` after a successful build, connecting to the VPS over SSH and executing `git pull origin developer` followed by `docker compose up -d --build`.

### Required GitHub Secrets

Add the following secrets in the repository settings so the workflow can reach your VPS (values shown are examples; use your actual data):

| Secret | Description |
| --- | --- |
| `VPS_HOST` | VPS IP or hostname (e.g., `148.230.93.34`) |
| `VPS_USERNAME` | SSH username (e.g., `root`) |
| `VPS_PASSWORD` | SSH password for that user |
| `VPS_PORT` *(optional)* | SSH port, defaults to `22` if omitted |

Ensure the credentials are valid and that `smartreply-clone/` already exists on the server so the workflow commands succeed.
