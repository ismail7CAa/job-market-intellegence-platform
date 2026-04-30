# Infrastructure Setup Guide

Free-tier AWS deployment path with CI/CD and Docker, plus optional ECS/Terraform scaffolding for later production hardening.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    GitHub Actions CI/CD                 │
│  (Test → Build Docker → Push to GHCR → Deploy to EC2)  │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              AWS Free-Tier EC2 Host                      │
├─────────────────────────────────────────────────────────┤
│  Docker Compose                                           │
│  - FastAPI app from GHCR                                  │
│  - Local Postgres container with persistent volume         │
│  - No ECS, ALB, NAT gateway, RDS, or ElastiCache required  │
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

# 4. Run local developer workflows
make test
make ingest
make serve

# 5. Access the application
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

## Docker Deployment

### Build Docker Image

```bash
bash scripts/build-docker.sh job-market-intelligence-platform v1.0.0
```

### Push to GitHub Container Registry

The GitHub Actions workflow pushes images to GHCR automatically after tests pass.

## AWS Free-Tier EC2 Deployment

### Prerequisites
- One free-tier eligible EC2 instance
- Docker and the Docker Compose plugin installed on the EC2 host
- Security group inbound rules for SSH `22` and API traffic `8000`
- A deploy SSH key stored in GitHub Actions secrets

### GitHub Actions Secrets

```
EC2_HOST
EC2_USER
EC2_SSH_KEY
EC2_DB_PASSWORD
```

Optional:

```
EC2_PORT
EC2_APP_DIR
```

### Deploy Manually

```bash
bash scripts/deploy.sh
```

The script copies `docker-compose.free-tier.yml` and `database/init.sql` to the EC2 host, writes a remote `.env`, pulls the configured image, and restarts the app with Docker Compose.

## Optional AWS ECS/Terraform Deployment

The `terraform/` directory remains as production-oriented scaffolding. It provisions ECS Fargate, an Application Load Balancer, private networking, optional RDS, and optional ElastiCache. That path is not the default because those resources can create ongoing AWS charges.

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
5. **Deploy**: Deploy to AWS free-tier EC2 with Docker Compose (main branch only)

### GitHub Secrets Required

```
EC2_HOST
EC2_USER
EC2_SSH_KEY
EC2_DB_PASSWORD
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

## Cost Notes

The default deployment path is designed for a free-tier eligible EC2 instance and local Docker containers. Avoid enabling the Terraform ECS path unless you intentionally want managed AWS resources such as ALB, NAT gateways, RDS, and Fargate.

## Troubleshooting

### EC2 container won't start
```bash
cd ~/job-market-intelligence-platform
docker compose -f docker-compose.free-tier.yml logs -f app
```

### Database connection error
```bash
docker compose -f docker-compose.free-tier.yml logs -f postgres
```

### Deployment failed
```bash
# Check SSH access
ssh ubuntu@<EC2_HOST>

# Check remote containers
docker compose -f ~/job-market-intelligence-platform/docker-compose.free-tier.yml ps
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

### Stop EC2 Deployment
```bash
cd ~/job-market-intelligence-platform
docker compose -f docker-compose.free-tier.yml down
```

### Delete Optional Terraform Resources
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
