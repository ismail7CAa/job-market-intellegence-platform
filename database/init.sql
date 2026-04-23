#!/bin/bash

# Database initialization script
set -e

DB_NAME="${DB_NAME:-job_market}"
DB_USER="${DB_USER:-jobmarket}"

echo "Initializing PostgreSQL database..."

# Create database tables
psql -U "$DB_USER" -d "$DB_NAME" <<EOF

CREATE TABLE IF NOT EXISTS job_postings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(255) NOT NULL,
  company VARCHAR(255) NOT NULL,
  location VARCHAR(255),
  salary_min INTEGER,
  salary_max INTEGER,
  job_type VARCHAR(50),
  description TEXT,
  source VARCHAR(50),
  url TEXT,
  posted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS skills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) UNIQUE NOT NULL,
  category VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_skills (
  job_id UUID REFERENCES job_postings(id) ON DELETE CASCADE,
  skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
  PRIMARY KEY (job_id, skill_id)
);

CREATE TABLE IF NOT EXISTS skill_trends (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
  month DATE,
  occurrences INTEGER DEFAULT 0,
  salary_premium FLOAT,
  trend_percentage FLOAT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS salary_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  role VARCHAR(255),
  location VARCHAR(255),
  min_salary INTEGER,
  max_salary INTEGER,
  median_salary INTEGER,
  sample_size INTEGER,
  currency VARCHAR(10) DEFAULT 'USD',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_job_title ON job_postings(title);
CREATE INDEX IF NOT EXISTS idx_job_company ON job_postings(company);
CREATE INDEX IF NOT EXISTS idx_job_location ON job_postings(location);
CREATE INDEX IF NOT EXISTS idx_skill_trends_month ON skill_trends(month);

EOF

echo "✅ Database initialized successfully"
