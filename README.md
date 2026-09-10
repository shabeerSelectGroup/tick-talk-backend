# TickTalk

Monorepo for the TickTalk event platform.

| Path | Description |
|------|-------------|
| `app/` | FastAPI backend |
| `ui/` | Vue 3 + Vite admin & participant frontend |
| `scripts/deploy.sh` | Server-side API deploy (git pull, migrate, restart) |
| `scripts/deploy-ui.sh` | Manual UI build + publish to nginx dist |

## Deploy

Pushing to `main` runs `.github/workflows/deploy.yml`:

1. Builds `ui/` in GitHub Actions
2. Uploads the static bundle to the server
3. Runs `scripts/deploy.sh` for the API and extracts the UI into `/home/deploy/apps/ticktalk/dist`

SSH secrets (`SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, optional `SSH_PORT`) are configured on this repo only.

## Local development

```bash
# API
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# UI
cd ui && yarn install && yarn dev
```
