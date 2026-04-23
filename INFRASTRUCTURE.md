# Infrastructure Setup Guide

Complete AWS deployment infrastructure with CI/CD, Docker, Kubernetes, and IaC.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    GitHub Actions CI/CD                 │
│  (Test → Build Docker → Push to ECR → Deploy to ECS)   │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              AWS Infrastructure (Terraform)              │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────┐   │
│  │         VPC (10.0.0.0/16)                        │   │
│  │  ┌────────────────────────────────────────────┐  │   │
│  │  │  Public Subnets (Load Balancer)           │  │   │
│  │  └────────────────┬───────────────────────────┘  │   │
│  │                   │                               │   │
│  │  ┌────────────────▼───────────────────────────┐  │   │
│  │  │  ALB (Application Load Balancer)          │  │   │
│  │  └────────────────┬───────────────────────────┘  │   │
│  │                   │                               │   │
│  │  ┌────────────────▼───────────────────────────┐  │   │
│  │  │  Private Subnets (ECS Fargate)            │  │   │
│  │  │  - Task Definition                       │  │   │
│  │  │  - Service (Desired: 2-3 tasks)         │  │   │
│  │  │  - Auto Scaling (2-4 replicas)          │  │   │
│  │  └────────────────┬───────────────────────────┘  │   │
│  │                   │                               │   │
│  │  ┌────────────────┼───────────────────────────┐  │   │
│  │  │                │                           │  │   │
│  │  ▼                ▼                           ▼  │   │
│  │ RDS            Redis              Secrets Manager │   │
│  │ PostgreSQL     ElastiCache        (DB passwords)  │   │
│  │ (Multi-AZ)     (Optional)                         │   │
│  │                                                    │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Quick Start - Local Development

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Git

### Setup

```bash
# 1. Clone repository
git clone https://github.com/ismail7CAa/job-market-intellegence-platform.git
cd job-market-intellegence-platform

# 2. Create environment file
cp .env.example .env
# Edit .env with your settings

# 3. Start local environment
bash scripts/dev-setup.sh

# 4. Access the application
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

## Docker Deployment

### Build Docker Image

```bash
bash scripts/build-docker.sh job-market-intelligence-platform v1.0.0
```

### Push to AWS ECR

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT-ID>.dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag job-market-intelligence-platform:v1.0.0 <ACCOUNT-ID>.dkr.ecr.us-east-1.amazonaws.com/job-market-intelligence-platform:v1.0.0

# Push
docker push <ACCOUNT-ID>.dkr.ecr.us-east-1.amazonaws.com/job-market-intelligence-platform:v1.0.0
```

## AWS Deployment with Terraform

### Prerequisites
- AWS CLI configured
- Terraform >= 1.0
- AWS credentials with permissions

### Deploy to AWS

```bash
# 1. Initialize Terraform
cd terraform
terraform init

# 2. Create terraform.tfvars
cat > terraform.tfvars <<EOF
aws_region         = "us-east-1"
environment        = "prod"
container_image    = "your-account-id.dkr.ecr.us-east-1.amazonaws.com/job-market-intelligence-platform:v1.0.0"
db_password        = "your_secure_password"
enable_rds         = true
enable_elasticache = false
desired_count      = 2
EOF

# 3. Validate
terraform validate

# 4. Plan
terraform plan -out=tfplan

# 5. Apply
terraform apply tfplan

# 6. Get outputs
terraform output
```

### Terraform Structure

```
terraform/
├── main.tf           # Provider configuration
├── variables.tf      # Input variables
├── networking.tf     # VPC, subnets, gateways
├── ecs.tf           # ECS cluster, service, tasks
├── database.tf      # RDS, ElastiCache
├── iam.tf           # IAM roles and policies
└── outputs.tf       # Output values
```

## GitHub Actions CI/CD

### Workflow Events
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

### Workflow Steps

1. **Test**: Run pytest with coverage
2. **Lint**: Pylint and Black code quality checks
3. **Build**: Multi-stage Docker build
4. **Push**: Push to GitHub Container Registry (GHCR)
5. **Deploy**: Deploy to AWS ECS (main branch only)

### GitHub Secrets Required

```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION
ECS_CLUSTER
ECS_SERVICE
```

## Kubernetes Deployment

### Install to Kubernetes Cluster

```bash
# 1. Create secrets
kubectl create secret generic postgres-secret \
  --from-literal=username=jobmarket \
  --from-literal=password=your_password

# 2. Create configmap
kubectl create configmap postgres-config \
  --from-literal=database-name=job_market

# 3. Deploy PostgreSQL
kubectl apply -f k8s/postgres.yaml

# 4. Deploy application
kubectl apply -f k8s/deployment.yaml

# 5. Verify deployment
kubectl get pods
kubectl get svc
```

### Monitor Deployment

```bash
# Watch rollout
kubectl rollout status deployment/jmip-app

# View logs
kubectl logs -f deployment/jmip-app

# Access application
kubectl port-forward svc/jmip-service 8000:80
# Then: http://localhost:8000
```

### Auto-scaling

- HPA configured to scale 2-10 replicas
- CPU target: 70% utilization
- Memory target: 80% utilization

## Database Setup

### PostgreSQL Schema

Tables created automatically:
- `job_postings` - Main job listing data
- `skills` - Unique skills
- `job_skills` - Many-to-many relationship
- `skill_trends` - Historical trend data
- `salary_data` - Salary statistics
- `market_forecasts` - Predicted trends
- `pipeline_logs` - Data pipeline logs

### Connect to RDS

```bash
# Get RDS endpoint
aws rds describe-db-instances --query 'DBInstances[0].Endpoint.Address'

# Connect
psql -h <rds-endpoint> -U admin -d job_market
```

## Monitoring & Logging

### CloudWatch
- Log Group: `/ecs/jmip`
- Retention: 7 days (configurable)

### Health Checks
- **Liveness Probe**: `/health` endpoint every 30s
- **Readiness Probe**: `/health` endpoint every 10s

### Alarms (optional)
Configure in Terraform:
- High CPU utilization
- High memory usage
- Failed tasks
- Database connection errors

## Costs Estimation (AWS)

| Component | Type | Estimate |
|-----------|------|----------|
| ECS Fargate | 2 tasks (0.25 CPU, 512 MB) | ~$15/month |
| RDS PostgreSQL | db.t3.micro | ~$20/month |
| Application Load Balancer | ALB | ~$20/month |
| Data Transfer | Outbound | ~$5/month |
| **Total** | | **~$60/month** |

*Note: Production setup (multi-AZ, larger instances) will cost more.*

## Troubleshooting

### ECS Task won't start
```bash
# Check task logs
aws logs tail /ecs/jmip --follow
```

### Database connection error
```bash
# Verify security group allows inbound
aws ec2 describe-security-groups --query "SecurityGroups[?GroupName=='jmip-rds-sg']"
```

### Deployment failed
```bash
# Check Terraform state
terraform show | grep -i error

# Force refresh
terraform refresh
```

## Security Best Practices

✅ Implemented:
- Non-root Docker user
- Secrets Manager for passwords
- VPC with public/private subnets
- Security groups with minimal permissions
- Multi-AZ for production
- Encrypted RDS storage
- Health checks and auto-recovery

## Cleanup

### Delete AWS Resources
```bash
cd terraform
terraform destroy
```

### Delete Kubernetes Resources
```bash
kubectl delete -f k8s/
```

### Stop Local Services
```bash
docker-compose down -v
```

## Next Steps

1. ✅ Set up GitHub Actions secrets
2. ✅ Configure custom domain (Route 53)
3. ✅ Set up auto-scaling policies
4. ✅ Enable CloudWatch alarms
5. ✅ Configure backup strategy
6. ✅ Set up monitoring dashboard
