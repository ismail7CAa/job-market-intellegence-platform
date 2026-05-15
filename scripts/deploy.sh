#!/bin/bash
set -euo pipefail

echo "Deploying Job Market Intelligence Platform to an AWS free-tier EC2 host..."
echo ""

if ! command -v ssh >/dev/null 2>&1; then
    echo "ssh not found. Please install OpenSSH first."
    exit 1
fi

if ! command -v scp >/dev/null 2>&1; then
    echo "scp not found. Please install OpenSSH first."
    exit 1
fi

read -p "EC2 host or public IP: " EC2_HOST
read -p "EC2 SSH user (default: ubuntu): " EC2_USER
EC2_USER=${EC2_USER:-ubuntu}

read -p "SSH key path (default: ~/.ssh/id_rsa): " EC2_SSH_KEY
EC2_SSH_KEY=${EC2_SSH_KEY:-~/.ssh/id_rsa}
EC2_SSH_KEY=${EC2_SSH_KEY/#\~/$HOME}

read -p "Remote app directory (default: ~/job-market-intelligence-platform): " EC2_APP_DIR
EC2_APP_DIR=${EC2_APP_DIR:-~/job-market-intelligence-platform}

read -p "Container image URI (for example ghcr.io/user/repo:main): " APP_IMAGE
if [[ -z "$APP_IMAGE" ]]; then
    echo "Container image URI is required."
    exit 1
fi

read -p "GHCR username for private images (optional): " GHCR_USERNAME
GHCR_TOKEN=""
if [[ -n "$GHCR_USERNAME" ]]; then
    read -rsp "GHCR token with package read access: " GHCR_TOKEN
    echo ""
fi

read -p "Database user (default: jobmarket): " DB_USER
DB_USER=${DB_USER:-jobmarket}

read -p "Database name (default: job_market): " DB_NAME
DB_NAME=${DB_NAME:-job_market}

read -rsp "Database password: " DB_PASSWORD
echo ""
if [[ -z "$DB_PASSWORD" ]]; then
    echo "Database password is required."
    exit 1
fi

echo "Preparing remote directory..."
ssh -i "$EC2_SSH_KEY" "$EC2_USER@$EC2_HOST" "mkdir -p $EC2_APP_DIR/database"

echo "Copying deployment files..."
scp -i "$EC2_SSH_KEY" docker-compose.free-tier.yml "$EC2_USER@$EC2_HOST:$EC2_APP_DIR/docker-compose.free-tier.yml"
scp -i "$EC2_SSH_KEY" database/init.sql "$EC2_USER@$EC2_HOST:$EC2_APP_DIR/database/init.sql"

echo "Starting containers on EC2..."
ssh -i "$EC2_SSH_KEY" "$EC2_USER@$EC2_HOST" <<EOF
set -e
cd $EC2_APP_DIR

cat > .env <<ENVEOF
APP_IMAGE=$APP_IMAGE
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_NAME=$DB_NAME
DEBUG=false
LOG_LEVEL=INFO
MARKET_REGION=Germany
DEFAULT_CURRENCY=EUR
ENVEOF

if [[ -n "$GHCR_USERNAME" && -n "$GHCR_TOKEN" ]]; then
    echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin
fi

docker compose -f docker-compose.free-tier.yml pull
docker compose -f docker-compose.free-tier.yml up -d --remove-orphans
docker image prune -f
EOF

echo ""
echo "Deployment complete."
echo "API: http://$EC2_HOST:8000"
