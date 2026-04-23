{{ config(materialized='table') }}

WITH skill_exploded AS (
    SELECT
        id as job_id,
        skill,
        posted_date,
        location,
        company,
        salary_min,
        salary_max,
        source
    FROM {{ ref('int_job_postings') }},
    UNNEST(required_skills) as skill
),

skill_trends AS (
    SELECT
        skill,
        DATE_TRUNC(posted_date, MONTH) as month,
        COUNT(DISTINCT job_id) as job_count,
        COUNT(DISTINCT company) as company_count,
        AVG((salary_min + salary_max) / 2) as avg_salary,
        ARRAY_AGG(DISTINCT location LIMIT 10) as top_locations
    FROM skill_exploded
    WHERE posted_date IS NOT NULL
    GROUP BY skill, DATE_TRUNC(posted_date, MONTH)
)

SELECT * FROM skill_trends