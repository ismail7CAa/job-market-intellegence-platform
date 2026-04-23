#!/bin/bash
set -e

echo "🚀 Deploying Job Market Intelligence Platform..."
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first."
    exit 1
fi

# Check Terraform
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform not found. Please install it first."
    exit 1
fi

# Get AWS region
read -p "Enter AWS region (default: us-east-1): " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

# Get environment
read -p "Enter environment (dev/staging/prod): " ENVIRONMENT
ENVIRONMENT=${ENVIRONMENT:-dev}

# Get Docker image
read -p "Enter Docker image URI: " DOCKER_IMAGE

# Get database password
read -sp "Enter database password: " DB_PASSWORD
echo ""

# Create terraform.tfvars
cat > terraform/terraform.tfvars <<EOF
aws_region          = "$AWS_REGION"
environment         = "$ENVIRONMENT"
container_image     = "$DOCKER_IMAGE"
db_password         = "$DB_PASSWORD"
enable_rds          = true
enable_elasticache  = false
desired_count       = $([[ "$ENVIRONMENT" == "prod" ]] && echo "3" || echo "1")
EOF

echo "✅ Created terraform.tfvars"

# Initialize Terraform
cd terraform
echo "📦 Initializing Terraform..."
terraform init

# Validate
echo "✔️  Validating Terraform..."
terraform validate

# Plan
echo "📋 Creating Terraform plan..."
terraform plan -out=tfplan

# Apply
read -p "Apply Terraform changes? (yes/no): " APPLY
if [[ "$APPLY" == "yes" ]]; then
    echo "🔨 Applying Terraform configuration..."
    terraform apply tfplan
    
    # Get outputs
    echo ""
    echo "✅ Infrastructure deployed successfully!"
    echo ""
    echo "📍 Outputs:"
    terraform output
else
    echo "⏭️  Skipped Terraform apply"
fi

cd ..

echo ""
echo "🎯 Next steps:"
echo "1. Push Docker image to AWS ECR"
echo "2. Update ECS service with new image"
echo "3. Configure GitHub Actions secrets"
echo "4. Set up monitoring and alerts"
