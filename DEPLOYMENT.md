# VPS Deployment Guide

## Quick Deploy Commands

### First Time Setup
```bash
cd smartreply-clone
git pull origin main
docker-compose up --build -d
```

### Regular Updates (After Code Changes)
```bash
git pull origin main
docker-compose up --build -d
```

### Check Application Status
```bash
docker-compose ps
docker-compose logs -f
```

## Environment Variables

Make sure your `.env` file or `docker-compose.yml` has:
- `META_API_TOKEN` - Your Meta webhook token
- `PAGE_ACCESS_TOKEN` - Your Facebook page access token
- `GOOGLE_API_KEY` or `OPENAI_API_KEY` - LLM API key
- `LLM_PROVIDER` - "google" or "openai"
- `LLM_MODEL` - Model name (e.g., "gemini-2.5-flash")

## Useful Docker Commands

```bash
# View logs
docker-compose logs -f

# Stop application
docker-compose down

# Restart application
docker-compose restart

# Rebuild from scratch
docker-compose down && docker-compose up --build -d

# Access container shell
docker-compose exec smartreply-clone bash
```

## Application Access

- **Health Check:** http://your-vps-ip:8009/health
- **Webhook:** http://your-vps-ip:8009/webhook
- **API Docs:** http://your-vps-ip:8009/docs
- **Comments:** http://your-vps-ip:8009/comments
