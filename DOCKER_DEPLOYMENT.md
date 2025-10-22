# SmartReply Clone - Docker Deployment Guide

## Overview
This project is containerized using Docker and deployed with docker-compose following your workflow.

## Files Created
- `Dockerfile` - Container image definition
- `docker-compose.yml` - Deployment configuration
- `nginx.conf` - Nginx reverse proxy configuration

## Deployment Workflow

### 1. Build and Push Image
```bash
# Build the image
docker build -t yourusername/smartreply-clone:latest .

# Push to Docker Hub
docker push yourusername/smartreply-clone:latest
```

### 2. Deploy on VPS
```bash
# Pull latest image
docker pull yourusername/smartreply-clone:latest

# Start services
docker-compose up -d
```

## Configuration

### Docker Image
- **Base**: Python 3.12 slim
- **Package Manager**: uv
- **Port**: 8000
- **Health Check**: Built-in curl check
- **Security**: Non-root user

### Docker Compose
- **Service**: smartreply-clone
- **Restart Policy**: unless-stopped
- **Port Mapping**: 8000:8000
- **Environment Variables**: META_API_TOKEN, SENTRY_DSN, etc.
- **Volume**: logs directory for persistence

### Nginx Configuration
- **Domain**: smartreply.webdesigningcompanynewyork.com
- **Redirect**: www to non-www
- **Proxy**: Pass to localhost:8000
- **Timeouts**: Optimized for webhook processing
- **Security Headers**: Added for protection

## Environment Variables Required
- `META_API_TOKEN` - Facebook Meta API token
- `SENTRY_DSN` - Sentry error tracking DSN
- `RELEASE_VERSION` - Optional release version

## SSL Setup (After Deployment)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d smartreply.webdesigningcompanynewyork.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Monitoring
- Health check endpoint: `/webhook`
- Container logs: `docker-compose logs -f`
- Nginx logs: `/var/log/nginx/`

## Troubleshooting
- Check container status: `docker-compose ps`
- View logs: `docker-compose logs smartreply-clone`
- Restart service: `docker-compose restart smartreply-clone`
