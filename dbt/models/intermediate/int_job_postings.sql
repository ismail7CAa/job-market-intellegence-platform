{{ config(materialized='table') }}

WITH cleaned_jobs AS (
    SELECT
        id,
        LOWER(TRIM(title)) as title,
        LOWER(TRIM(company)) as company,
        LOWER(TRIM(location)) as location,
        description,
        CASE
            WHEN salary_min > 0 AND salary_max > 0 AND salary_min <= salary_max
            THEN salary_min
            ELSE NULL
        END as salary_min,
        CASE
            WHEN salary_min > 0 AND salary_max > 0 AND salary_min <= salary_max
            THEN salary_max
            ELSE NULL
        END as salary_max,
        ARRAY(
            SELECT LOWER(TRIM(skill))
            FROM UNNEST(required_skills) as skill
            WHERE TRIM(skill) != ''
        ) as required_skills,
        posted_date,
        source,
        ingested_at
    FROM {{ ref('stg_job_postings') }}
    WHERE title IS NOT NULL
      AND company IS NOT NULL
      AND location IS NOT NULL
),

deduplicated AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY title, company, location
               ORDER BY ingested_at DESC
           ) as rn
    FROM cleaned_jobs
)

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
FROM deduplicated
WHERE rn = 1