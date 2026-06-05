CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS job_postings (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  title VARCHAR(255) NOT NULL,
  company VARCHAR(255) NOT NULL,
  location VARCHAR(255),
  country VARCHAR(100) DEFAULT 'Germany',
  city VARCHAR(120),
  federal_state VARCHAR(120),
  salary_min INTEGER,
  salary_max INTEGER,
  salary_period VARCHAR(50),
  salary_is_estimated BOOLEAN DEFAULT FALSE,
  salary_confidence FLOAT,
  job_type VARCHAR(50),
  employment_type VARCHAR(80),
  description TEXT,
  required_skills TEXT,
  source VARCHAR(50),
  source_posting_id VARCHAR(255),
  url TEXT,
  application_url TEXT,
  company_career_url TEXT,
  remote_status VARCHAR(50),
  role_type VARCHAR(120),
  occupation_group VARCHAR(255),
  experience_level VARCHAR(80),
  source_legal_basis TEXT,
  ingestion_batch_id VARCHAR(120),
  posted_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  posted_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  last_seen_at TIMESTAMPTZ,
  is_expired BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT unique_job_source_posting UNIQUE (source, source_posting_id)
);

CREATE TABLE IF NOT EXISTS skills (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  name VARCHAR(100) UNIQUE NOT NULL,
  category VARCHAR(50),
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_skills (
  job_id TEXT REFERENCES job_postings(id) ON DELETE CASCADE,
  skill_id TEXT REFERENCES skills(id) ON DELETE CASCADE,
  PRIMARY KEY (job_id, skill_id)
);

CREATE TABLE IF NOT EXISTS skill_trends (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  skill_id TEXT REFERENCES skills(id) ON DELETE CASCADE,
  month TIMESTAMPTZ NOT NULL,
  occurrences INTEGER DEFAULT 0,
  percentage FLOAT,
  salary_premium FLOAT,
  growth_percentage FLOAT,
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT unique_skill_month UNIQUE (skill_id, month)
);

CREATE TABLE IF NOT EXISTS salary_data (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  role VARCHAR(255) NOT NULL,
  location VARCHAR(255),
  min_salary INTEGER,
  max_salary INTEGER,
  median_salary INTEGER,
  mean_salary FLOAT,
  std_dev FLOAT,
  sample_size INTEGER DEFAULT 0,
  currency VARCHAR(10) DEFAULT 'EUR',
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_job_title ON job_postings(title);
CREATE INDEX IF NOT EXISTS idx_job_company ON job_postings(company);
CREATE INDEX IF NOT EXISTS idx_job_location ON job_postings(location);
CREATE INDEX IF NOT EXISTS idx_job_city ON job_postings(city);
CREATE INDEX IF NOT EXISTS idx_job_federal_state ON job_postings(federal_state);
CREATE INDEX IF NOT EXISTS idx_job_source ON job_postings(source);
CREATE INDEX IF NOT EXISTS idx_job_source_posting_id ON job_postings(source_posting_id);
CREATE INDEX IF NOT EXISTS idx_job_remote_status ON job_postings(remote_status);
CREATE INDEX IF NOT EXISTS idx_job_role_type ON job_postings(role_type);
CREATE INDEX IF NOT EXISTS idx_job_occupation_group ON job_postings(occupation_group);
CREATE INDEX IF NOT EXISTS idx_job_experience_level ON job_postings(experience_level);
CREATE INDEX IF NOT EXISTS idx_job_ingestion_batch_id ON job_postings(ingestion_batch_id);
CREATE INDEX IF NOT EXISTS idx_job_posted_date ON job_postings(posted_date);
CREATE INDEX IF NOT EXISTS idx_job_posted_at ON job_postings(posted_at);
CREATE INDEX IF NOT EXISTS idx_job_expires_at ON job_postings(expires_at);
CREATE INDEX IF NOT EXISTS idx_job_last_seen_at ON job_postings(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_job_is_expired ON job_postings(is_expired);
CREATE INDEX IF NOT EXISTS idx_skill_name ON skills(name);
CREATE INDEX IF NOT EXISTS idx_skill_trends_month ON skill_trends(month);
CREATE INDEX IF NOT EXISTS idx_salary_role ON salary_data(role);
CREATE INDEX IF NOT EXISTS idx_salary_location ON salary_data(location);
