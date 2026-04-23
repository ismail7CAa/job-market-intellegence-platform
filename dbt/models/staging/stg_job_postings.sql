{{ config(materialized='table') }}

SELECT
    id,
    title,
    company,
    location,
    description,
    salary_min,
    salary_max,
    required_skills,
    posted_date,
    source,
    ingested_at
FROM {{ source('bronze', 'raw_job_postings') }}