{{
  config(
    materialized='table',
    description='Fatos agregados para análise de tendências do mercado de trabalho',
    indexes=[
      {'columns': ['trend_date'], 'type': 'btree'},
      {'columns': ['source'], 'type': 'btree'},
      {'columns': ['state'], 'type': 'btree'},
      {'columns': ['seniority_level'], 'type': 'btree'}
    ]
  )
}}

WITH job_data AS (
  SELECT * FROM {{ ref('int_jobs') }}
  WHERE scraped_at >= CURRENT_DATE - INTERVAL '90 days'  -- Últimos 90 dias
),

-- Agregações diárias por diferentes dimensões
daily_trends AS (
  SELECT 
    DATE(scraped_at) AS trend_date,
    source,
    state,
    seniority_level,
    work_mode,
    tech_stack_category,
    cloud_preference,
    
    -- Contagens básicas
    COUNT(*) AS total_jobs,
    COUNT(DISTINCT company) AS unique_companies,
    COUNT(CASE WHEN salary IS NOT NULL THEN 1 END) AS jobs_with_salary,
    COUNT(CASE WHEN is_premium_job THEN 1 END) AS premium_jobs,
    
    -- Métricas de skills
    AVG(technical_skills_score) AS avg_technical_score,
    AVG(total_skills_count) AS avg_skills_count,
    
    -- Skills mais demandadas (percentual)
    ROUND(AVG(has_python::int) * 100, 2) AS python_demand_pct,
    ROUND(AVG(has_sql::int) * 100, 2) AS sql_demand_pct,
    ROUND(AVG(has_bigdata::int) * 100, 2) AS bigdata_demand_pct,
    ROUND(AVG(has_orchestration::int) * 100, 2) AS orchestration_demand_pct,
    ROUND(AVG(has_dbt::int) * 100, 2) AS dbt_demand_pct,
    ROUND(AVG(has_aws::int) * 100, 2) AS aws_demand_pct,
    ROUND(AVG(has_azure::int) * 100, 2) AS azure_demand_pct,
    ROUND(AVG(has_gcp::int) * 100, 2) AS gcp_demand_pct,
    ROUND(AVG(has_datawarehouse::int) * 100, 2) AS datawarehouse_demand_pct,
    ROUND(AVG(has_streaming::int) * 100, 2) AS streaming_demand_pct,
    ROUND(AVG(has_containers::int) * 100, 2) AS containers_demand_pct,
    ROUND(AVG(has_ml::int) * 100, 2) AS ml_demand_pct,
    ROUND(AVG(has_visualization::int) * 100, 2) AS visualization_demand_pct,
    
    -- Benefícios (percentual)
    ROUND(AVG(has_meal_voucher::int) * 100, 2) AS meal_voucher_pct,
    ROUND(AVG(has_health_insurance::int) * 100, 2) AS health_insurance_pct,
    ROUND(AVG(has_flexible_hours::int) * 100, 2) AS flexible_hours_pct,
    
    -- Experiência requerida
    AVG(required_experience_years) AS avg_required_experience,
    
    CURRENT_TIMESTAMP AS calculated_at
    
  FROM job_data
  GROUP BY 1, 2, 3, 4, 5, 6, 7
),

-- Tendências semanais
weekly_trends AS (
  SELECT 
    DATE_TRUNC('week', scraped_at) AS trend_week,
    source,
    state,
    
    COUNT(*) AS total_jobs,
    COUNT(DISTINCT company) AS unique_companies,
    AVG(technical_skills_score) AS avg_technical_score,
    
    -- Top 5 skills da semana
    ROUND(AVG(has_python::int) * 100, 2) AS python_demand_pct,
    ROUND(AVG(has_sql::int) * 100, 2) AS sql_demand_pct,
    ROUND(AVG(has_bigdata::int) * 100, 2) AS bigdata_demand_pct,
    ROUND(AVG(has_orchestration::int) * 100, 2) AS orchestration_demand_pct,
    ROUND(AVG(has_aws::int) * 100, 2) AS aws_demand_pct,
    
    CURRENT_TIMESTAMP AS calculated_at
    
  FROM job_data
  GROUP BY 1, 2, 3
),

-- Ranking de empresas que mais contratam
company_rankings AS (
  SELECT 
    DATE(scraped_at) AS trend_date,
    company,
    state,
    source,
    
    COUNT(*) AS jobs_posted,
    AVG(technical_skills_score) AS avg_technical_score,
    COUNT(CASE WHEN is_premium_job THEN 1 END) AS premium_jobs,
    
    -- Skills mais pedidas por empresa
    STRING_AGG(
      CASE 
        WHEN has_python THEN 'Python'
        WHEN has_sql THEN 'SQL'
        WHEN has_bigdata THEN 'Big Data'
        WHEN has_orchestration THEN 'Airflow'
        WHEN has_aws THEN 'AWS'
        WHEN has_azure THEN 'Azure'
        WHEN has_gcp THEN 'GCP'
      END, ', '
    ) AS top_skills_required,
    
    CURRENT_TIMESTAMP AS calculated_at
    
  FROM job_data
  WHERE company != 'Não informado'
  GROUP BY 1, 2, 3, 4
  HAVING COUNT(*) >= 2  -- Empresas com pelo menos 2 vagas
),

-- Análise de salários (quando disponível)
salary_trends AS (
  SELECT 
    DATE(scraped_at) AS trend_date,
    state,
    seniority_level,
    
    COUNT(CASE WHEN salary IS NOT NULL THEN 1 END) AS jobs_with_salary,
    COUNT(*) AS total_jobs,
    ROUND(
      COUNT(CASE WHEN salary IS NOT NULL THEN 1 END)::NUMERIC / COUNT(*) * 100, 
      2
    ) AS salary_disclosure_rate,
    
    -- Tentativa de extrair ranges salariais (simplificado)
    COUNT(CASE WHEN salary ~ '\d{4,}' THEN 1 END) AS jobs_with_numeric_salary,
    
    CURRENT_TIMESTAMP AS calculated_at
    
  FROM job_data
  GROUP BY 1, 2, 3
),

-- Consolidação final
final AS (
  SELECT 
    'daily' AS aggregation_level,
    trend_date AS period_start,
    trend_date AS period_end,
    source,
    state,
    seniority_level,
    work_mode,
    tech_stack_category,
    cloud_preference,
    total_jobs,
    unique_companies,
    jobs_with_salary,
    premium_jobs,
    avg_technical_score,
    avg_skills_count,
    python_demand_pct,
    sql_demand_pct,
    bigdata_demand_pct,
    orchestration_demand_pct,
    dbt_demand_pct,
    aws_demand_pct,
    azure_demand_pct,
    gcp_demand_pct,
    datawarehouse_demand_pct,
    streaming_demand_pct,
    containers_demand_pct,
    ml_demand_pct,
    visualization_demand_pct,
    meal_voucher_pct,
    health_insurance_pct,
    flexible_hours_pct,
    avg_required_experience,
    calculated_at
  FROM daily_trends
  
  UNION ALL
  
  SELECT 
    'weekly' AS aggregation_level,
    trend_week AS period_start,
    trend_week + INTERVAL '6 days' AS period_end,
    source,
    state,
    NULL AS seniority_level,
    NULL AS work_mode,
    NULL AS tech_stack_category,
    NULL AS cloud_preference,
    total_jobs,
    unique_companies,
    NULL AS jobs_with_salary,
    NULL AS premium_jobs,
    avg_technical_score,
    NULL AS avg_skills_count,
    python_demand_pct,
    sql_demand_pct,
    bigdata_demand_pct,
    orchestration_demand_pct,
    NULL AS dbt_demand_pct,
    aws_demand_pct,
    NULL AS azure_demand_pct,
    NULL AS gcp_demand_pct,
    NULL AS datawarehouse_demand_pct,
    NULL AS streaming_demand_pct,
    NULL AS containers_demand_pct,
    NULL AS ml_demand_pct,
    NULL AS visualization_demand_pct,
    NULL AS meal_voucher_pct,
    NULL AS health_insurance_pct,
    NULL AS flexible_hours_pct,
    NULL AS avg_required_experience,
    calculated_at
  FROM weekly_trends
)

SELECT * FROM final
WHERE period_start >= CURRENT_DATE - INTERVAL '30 days'  -- Últimos 30 dias
ORDER BY period_start DESC, source, state
