# GitHub Actions CI/CD Setup Guide

## Secrets Configuration

Add these secrets to your GitHub repository settings:

### AWS Free-Tier EC2 Secrets
```
EC2_HOST                   - EC2 public DNS name or public IP
EC2_USER                   - SSH user, usually ubuntu or ec2-user
EC2_SSH_KEY                - Private SSH key with access to the EC2 host
EC2_DB_PASSWORD            - Password for the local Postgres container
```

Optional:

```
EC2_PORT                   - SSH port, defaults to 22
EC2_APP_DIR                - Remote app directory, defaults to ~/job-market-intelligence-platform
```

### How to Add Secrets

1. Go to: GitHub Repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret with its value

## Workflow Triggers

The CI/CD pipeline runs automatically on:
- Push to `main` branch
- Push to `develop` branch  
- Pull requests to `main` and `develop` branches

## Workflow Steps

### 1. Test (Always runs)
```
✓ Set up Python 3.11
✓ Install dependencies
✓ Run Pytest with coverage
✓ Upload coverage to Codecov
```

### 2. Build (After tests pass)
```
✓ Set up Docker Buildx
✓ Log in to GitHub Container Registry (GHCR)
✓ Build multi-stage Docker image
✓ Push image with tags:
  - main → latest
  - Semantic version tags
  - Git SHA
```

### 3. Deploy (main branch only)
```
✓ Connect to the EC2 host over SSH
✓ Copy docker-compose.free-tier.yml and database/init.sql
✓ Pull the GHCR image
✓ Restart the app and local Postgres with Docker Compose
```

## EC2 Host Setup

Create one AWS free-tier eligible EC2 instance and install Docker plus the Docker Compose plugin.

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Open inbound port `22` for SSH and `8000` for the API in the EC2 security group. No AWS access keys, ECS cluster, ALB, NAT gateway, or RDS database are required for this deployment path.

## Environment Variables

The workflow sets these environment variables:
- `REGISTRY`: ghcr.io
- `IMAGE_NAME`: ${{ github.repository }}

## Docker Image Tags

Images are tagged with:
- `branch-name` - Current branch
- `semantic-version` - Release tags (v1.0.0)
- `git-sha` - Short commit SHA

Example:
```
ghcr.io/yourname/repo:main
ghcr.io/yourname/repo:v1.0.0
ghcr.io/yourname/repo:abc1234
```

## View Workflow Runs

1. Go to: GitHub Repo → Actions
2. Click on workflow run to view logs
3. Expand each job to see detailed output

## Troubleshooting

### Tests failing
```bash
# Run tests locally
pytest tests/ -v
```

### Docker build failing
```bash
# Test Docker build locally
docker build -t test:latest .
```

### Deployment failing
```bash
# Check SSH connectivity
ssh ubuntu@<EC2_HOST>

# Check Docker on the EC2 host
docker compose version
```

## Manual Deployment

If automated deployment fails:

```bash
bash scripts/deploy.sh
```

## Monitoring Deployments

### EC2 Docker Logs
```bash
cd ~/job-market-intelligence-platform
docker compose -f docker-compose.free-tier.yml ps
docker compose -f docker-compose.free-tier.yml logs -f app
```

The API is exposed on `http://<EC2_HOST>:8000`.
