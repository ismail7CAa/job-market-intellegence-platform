# GitHub Actions CI/CD Setup Guide

## Secrets Configuration

Add these secrets to your GitHub repository settings:

### AWS Secrets
```
AWS_ACCESS_KEY_ID          - Your AWS access key
AWS_SECRET_ACCESS_KEY      - Your AWS secret access key
AWS_REGION                 - AWS region (e.g., us-east-1)
```

### ECS Secrets
```
ECS_CLUSTER                - ECS cluster name (created by Terraform)
ECS_SERVICE                - ECS service name (created by Terraform)
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
✓ Configure AWS credentials
✓ Update ECS service with new image
✓ Force new deployment
```

## IAM Policy (AWS)

Attach this policy to the IAM user for CI/CD:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:UpdateService",
        "ecs:DescribeServices"
      ],
      "Resource": "arn:aws:ecs:*:*:service/*/*"
    }
  ]
}
```

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
# Check AWS credentials
aws sts get-caller-identity

# Verify ECS cluster exists
aws ecs list-clusters
```

## Manual Deployment

If automated deployment fails:

```bash
# Update ECS service manually
aws ecs update-service \
  --cluster jmip-cluster \
  --service jmip-service \
  --force-new-deployment
```

## Monitoring Deployments

### CloudWatch
```bash
# View recent deployments
aws ecs describe-services \
  --cluster jmip-cluster \
  --services jmip-service
```

### ECS Console
1. Go to AWS ECS Console
2. Select cluster: `jmip-cluster`
3. Select service: `jmip-service`
4. View task status and logs
