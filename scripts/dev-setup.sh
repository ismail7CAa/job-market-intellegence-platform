#!/bin/bash
set -e

echo "🚀 Starting local development environment..."

# Check if docker-compose exists
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found"
    exit 1
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  .env file not found, creating from .env.example..."
    cp .env.example .env
    echo "✏️  Please edit .env with your API keys"
fi

# Start services
echo "🐳 Starting Docker Compose services..."
docker-compose up -d

echo "⏳ Waiting for services to be healthy..."
sleep 10

# Run database migrations
echo "🗄️  Running database initialization..."
docker-compose exec -T postgres psql -U jobmarket -d job_market -f /docker-entrypoint-initdb.d/init.sql

echo "✅ Local environment is ready!"
echo ""
echo "Services running:"
echo "  📱 API: http://localhost:8000"
echo "  🗄️  PostgreSQL: localhost:5432"
echo "  🔴 Redis: localhost:6379"
echo ""
echo "View logs: docker-compose logs -f"
echo "Stop: docker-compose down"
