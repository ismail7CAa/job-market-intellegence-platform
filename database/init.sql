CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS job_postings (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  title VARCHAR(255) NOT NULL,
  company VARCHAR(255) NOT NULL,
  location VARCHAR(255),
  salary_min INTEGER,
  salary_max INTEGER,
  job_type VARCHAR(50),
  description TEXT,
  source VARCHAR(50),
  url TEXT,
  posted_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
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
CREATE INDEX IF NOT EXISTS idx_job_source ON job_postings(source);
CREATE INDEX IF NOT EXISTS idx_job_posted_date ON job_postings(posted_date);
CREATE INDEX IF NOT EXISTS idx_skill_name ON skills(name);
CREATE INDEX IF NOT EXISTS idx_skill_trends_month ON skill_trends(month);
CREATE INDEX IF NOT EXISTS idx_salary_role ON salary_data(role);
CREATE INDEX IF NOT EXISTS idx_salary_location ON salary_data(location);
