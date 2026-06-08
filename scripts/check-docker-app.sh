#!/bin/bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
SEARCH_QUERY="${SEARCH_QUERY:-Pflege}"
SEARCH_LOCATION="${SEARCH_LOCATION:-Berlin}"

echo "Checking Docker Compose services..."
docker compose ps --status running app postgres >/dev/null

if ! docker compose ps --status running app | grep -q "jmip_app"; then
    echo "jmip_app is not running. Start it with: docker compose up --build app"
    exit 1
fi

if ! docker compose ps --status running postgres | grep -q "jmip_postgres"; then
    echo "jmip_postgres is not running. Start it with: docker compose up --build app"
    exit 1
fi

echo "Checking health endpoint..."
health_payload="$(curl -fsS "$BASE_URL/health")"
echo "$health_payload" | grep -q '"status":"healthy"'

echo "Checking frontend route..."
curl -fsS "$BASE_URL/job-intelligence/" >/dev/null

echo "Checking search endpoint..."
search_payload="$(curl -fsS --get "$BASE_URL/jobs/search" \
    --data-urlencode "q=$SEARCH_QUERY" \
    --data-urlencode "location=$SEARCH_LOCATION" \
    --data-urlencode "per_page=1")"

echo "$search_payload" | grep -q '"count":1'
echo "$search_payload" | grep -q '"jobs":'
echo "$search_payload" | grep -q '"apply_endpoint":'

echo "Docker app check passed."
echo "Dashboard: $BASE_URL/job-intelligence/"
