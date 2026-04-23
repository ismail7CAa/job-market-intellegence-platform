#!/bin/bash
set -e

echo "🐳 Building Docker image..."

# Get image name and tag
IMAGE_NAME=${1:-"job-market-intelligence-platform"}
IMAGE_TAG=${2:-"latest"}

# Build
docker build -t "$IMAGE_NAME:$IMAGE_TAG" -t "$IMAGE_NAME:latest" .

echo "✅ Docker image built successfully"
echo "📝 Image: $IMAGE_NAME:$IMAGE_TAG"
echo ""
echo "Next: Push to registry"
echo "docker push $IMAGE_NAME:$IMAGE_TAG"
