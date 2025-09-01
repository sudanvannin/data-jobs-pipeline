{{
  config(
    materialized='view',
    description='Camada intermediária - extração de skills e enriquecimento dos dados'
  )
}}

WITH staged_jobs AS (
  SELECT * FROM {{ ref('stg_jobs') }}
  WHERE is_valid_job = TRUE
),

-- Extração de skills técnicas
skills_extraction AS (
  SELECT 
    *,
    
    -- Skills Python
    CASE WHEN description_lower ~ '\bpython\b' OR title_lower ~ '\bpython\b' THEN TRUE ELSE FALSE END AS has_python,
    
    -- Skills SQL
    CASE WHEN description_lower ~ '\bsql\b|\bpostgresql\b|\bmysql\b|\bsqlserver\b' 
              OR title_lower ~ '\bsql\b|\bpostgresql\b|\bmysql\b|\bsqlserver\b' THEN TRUE ELSE FALSE END AS has_sql,
    
    -- Big Data / Spark
    CASE WHEN description_lower ~ '\bspark\b|\bhadoop\b|\bhive\b|\bpresto\b|\bflink\b' 
              OR title_lower ~ '\bspark\b|\bhadoop\b|\bhive\b|\bpresto\b|\bflink\b' THEN TRUE ELSE FALSE END AS has_bigdata,
    
    -- Orquestração
    CASE WHEN description_lower ~ '\bairflow\b|\bprefect\b|\bdagster\b|\bkubeflow\b' 
              OR title_lower ~ '\bairflow\b|\bprefect\b|\bdagster\b|\bkubeflow\b' THEN TRUE ELSE FALSE END AS has_orchestration,
    
    -- DBT
    CASE WHEN description_lower ~ '\bdbt\b|\bdata build tool\b' 
              OR title_lower ~ '\bdbt\b|\bdata build tool\b' THEN TRUE ELSE FALSE END AS has_dbt,
    
    -- Cloud Providers
    CASE WHEN description_lower ~ '\baws\b|\bamazon web services\b|\bs3\b|\bredshift\b|\bec2\b' 
              OR title_lower ~ '\baws\b|\bamazon web services\b|\bs3\b|\bredshift\b|\bec2\b' THEN TRUE ELSE FALSE END AS has_aws,
              
    CASE WHEN description_lower ~ '\bazure\b|\bmicrosoft azure\b|\bblob storage\b|\bsynapse\b' 
              OR title_lower ~ '\bazure\b|\bmicrosoft azure\b|\bblob storage\b|\bsynapse\b' THEN TRUE ELSE FALSE END AS has_azure,
              
    CASE WHEN description_lower ~ '\bgcp\b|\bgoogle cloud\b|\bbigquery\b|\bcloud storage\b' 
              OR title_lower ~ '\bgcp\b|\bgoogle cloud\b|\bbigquery\b|\bcloud storage\b' THEN TRUE ELSE FALSE END AS has_gcp,
    
    -- Data Warehouses
    CASE WHEN description_lower ~ '\bsnowflake\b|\bredshift\b|\bbigquery\b|\bsynapse\b' 
              OR title_lower ~ '\bsnowflake\b|\bredshift\b|\bbigquery\b|\bsynapse\b' THEN TRUE ELSE FALSE END AS has_datawarehouse,
    
    -- Streaming
    CASE WHEN description_lower ~ '\bkafka\b|\bkinesis\b|\bpubsub\b|\beventhub\b|\bpulsar\b' 
              OR title_lower ~ '\bkafka\b|\bkinesis\b|\bpubsub\b|\beventhub\b|\bpulsar\b' THEN TRUE ELSE FALSE END AS has_streaming,
    
    -- Containers
    CASE WHEN description_lower ~ '\bdocker\b|\bkubernetes\b|\bk8s\b|\bcontainer\b' 
              OR title_lower ~ '\bdocker\b|\bkubernetes\b|\bk8s\b|\bcontainer\b' THEN TRUE ELSE FALSE END AS has_containers,
    
    -- Data Science / ML
    CASE WHEN description_lower ~ '\bmachine learning\b|\bml\b|\bscikit-learn\b|\btensorflow\b|\bpytorch\b|\bmlflow\b' 
              OR title_lower ~ '\bmachine learning\b|\bml\b|\bscikit-learn\b|\btensorflow\b|\bpytorch\b|\bmlflow\b' THEN TRUE ELSE FALSE END AS has_ml,
    
    -- Visualization Tools
    CASE WHEN description_lower ~ '\btableau\b|\bpower bi\b|\blooker\b|\bmetabase\b|\bsuperset\b|\bqlik\b' 
              OR title_lower ~ '\btableau\b|\bpower bi\b|\blooker\b|\bmetabase\b|\bsuperset\b|\bqlik\b' THEN TRUE ELSE FALSE END AS has_visualization,
    
    -- NoSQL
    CASE WHEN description_lower ~ '\bmongodb\b|\bcassandra\b|\belasticsearch\b|\bredis\b|\bdynamodb\b' 
              OR title_lower ~ '\bmongodb\b|\bcassandra\b|\belasticsearch\b|\bredis\b|\bdynamodb\b' THEN TRUE ELSE FALSE END AS has_nosql,
    
    -- Programming Languages (além do Python)
    CASE WHEN description_lower ~ '\bscala\b' OR title_lower ~ '\bscala\b' THEN TRUE ELSE FALSE END AS has_scala,
    CASE WHEN description_lower ~ '\bjava\b' OR title_lower ~ '\bjava\b' THEN TRUE ELSE FALSE END AS has_java,
    CASE WHEN description_lower ~ '\br\b|\br programming\b' OR title_lower ~ '\br\b|\br programming\b' THEN TRUE ELSE FALSE END AS has_r,
    
    -- DevOps / Infrastructure
    CASE WHEN description_lower ~ '\bterraform\b|\bansible\b|\bjenkins\b|\bgitlab ci\b|\bgithub actions\b' 
              OR title_lower ~ '\bterraform\b|\bansible\b|\bjenkins\b|\bgitlab ci\b|\bgithub actions\b' THEN TRUE ELSE FALSE END AS has_devops,
    
    -- Git
    CASE WHEN description_lower ~ '\bgit\b|\bgithub\b|\bgitlab\b|\bbitbucket\b' 
              OR title_lower ~ '\bgit\b|\bgithub\b|\bgitlab\b|\bbitbucket\b' THEN TRUE ELSE FALSE END AS has_git
    
  FROM staged_jobs
),

-- Cálculo de scores e métricas
enriched_jobs AS (
  SELECT 
    *,
    
    -- Score de skills técnicas (0-100)
    (
      (has_python::int * 10) +
      (has_sql::int * 15) +
      (has_bigdata::int * 8) +
      (has_orchestration::int * 7) +
      (has_dbt::int * 5) +
      (has_aws::int * 6) +
      (has_azure::int * 6) +
      (has_gcp::int * 6) +
      (has_datawarehouse::int * 8) +
      (has_streaming::int * 7) +
      (has_containers::int * 5) +
      (has_ml::int * 4) +
      (has_visualization::int * 3) +
      (has_nosql::int * 4) +
      (has_scala::int * 3) +
      (has_java::int * 3) +
      (has_r::int * 2) +
      (has_devops::int * 4) +
      (has_git::int * 2)
    ) AS technical_skills_score,
    
    -- Contagem total de skills
    (
      has_python::int +
      has_sql::int +
      has_bigdata::int +
      has_orchestration::int +
      has_dbt::int +
      has_aws::int +
      has_azure::int +
      has_gcp::int +
      has_datawarehouse::int +
      has_streaming::int +
      has_containers::int +
      has_ml::int +
      has_visualization::int +
      has_nosql::int +
      has_scala::int +
      has_java::int +
      has_r::int +
      has_devops::int +
      has_git::int
    ) AS total_skills_count,
    
    -- Classificação por stack tecnológico principal
    CASE 
      WHEN has_bigdata AND has_spark THEN 'Big Data'
      WHEN has_ml AND (has_python OR has_r) THEN 'Data Science/ML'
      WHEN has_streaming AND has_kafka THEN 'Real-time/Streaming'
      WHEN has_datawarehouse AND has_sql THEN 'Data Warehouse/Analytics'
      WHEN has_orchestration AND has_python THEN 'Data Engineering'
      WHEN has_visualization THEN 'Analytics/BI'
      ELSE 'Geral'
    END AS tech_stack_category,
    
    -- Classificação por nível de Cloud
    CASE 
      WHEN (has_aws::int + has_azure::int + has_gcp::int) >= 2 THEN 'Multi-cloud'
      WHEN has_aws THEN 'AWS'
      WHEN has_azure THEN 'Azure'
      WHEN has_gcp THEN 'GCP'
      ELSE 'On-premise/Não especificado'
    END AS cloud_preference,
    
    -- Flags para vagas premium (alta demanda de skills)
    CASE 
      WHEN technical_skills_score >= 50 THEN TRUE
      ELSE FALSE
    END AS is_premium_job,
    
    -- Extração de anos de experiência (regex simples)
    CASE 
      WHEN description_lower ~ '\b(\d+)\s*anos?\s*(de\s*)?experiência\b' THEN 
        CAST(SUBSTRING(description_lower FROM '\b(\d+)\s*anos?\s*(de\s*)?experiência\b') AS INTEGER)
      WHEN description_lower ~ '\b(\d+)\+?\s*years?\s*(of\s*)?experience\b' THEN 
        CAST(SUBSTRING(description_lower FROM '\b(\d+)\+?\s*years?\s*(of\s*)?experience\b') AS INTEGER)
      ELSE NULL
    END AS required_experience_years,
    
    -- Flags para benefícios comuns
    CASE WHEN description_lower ~ '\bvale\s*(refeição|alimentação)\b|\bvr\b|\bva\b' THEN TRUE ELSE FALSE END AS has_meal_voucher,
    CASE WHEN description_lower ~ '\bplano\s*de\s*saúde\b|\bsaúde\b|\bmedical\b' THEN TRUE ELSE FALSE END AS has_health_insurance,
    CASE WHEN description_lower ~ '\bplano\s*odontológico\b|\bdental\b' THEN TRUE ELSE FALSE END AS has_dental,
    CASE WHEN description_lower ~ '\bvale\s*transporte\b|\bvt\b|\btransporte\b' THEN TRUE ELSE FALSE END AS has_transport_voucher,
    CASE WHEN description_lower ~ '\bflexib\b|\bhorário\s*flexível\b' THEN TRUE ELSE FALSE END AS has_flexible_hours,
    CASE WHEN description_lower ~ '\bplu\b|\bparticipação\s*nos\s*lucros\b' THEN TRUE ELSE FALSE END AS has_profit_sharing,
    
    -- Data de processamento
    CURRENT_TIMESTAMP AS processed_at
    
  FROM skills_extraction
),

final AS (
  SELECT 
    -- IDs e informações básicas
    id,
    job_hash,
    
    -- Informações limpas da vaga
    title_clean AS title,
    company_clean AS company,
    location_clean AS location,
    state,
    description_clean AS description,
    salary_clean AS salary,
    work_mode,
    seniority_level,
    
    -- Datas
    date_posted,
    scraped_at,
    processed_at,
    
    -- URL e fonte
    url,
    source,
    
    -- Skills individuais
    has_python,
    has_sql,
    has_bigdata,
    has_orchestration,
    has_dbt,
    has_aws,
    has_azure,
    has_gcp,
    has_datawarehouse,
    has_streaming,
    has_containers,
    has_ml,
    has_visualization,
    has_nosql,
    has_scala,
    has_java,
    has_r,
    has_devops,
    has_git,
    
    -- Métricas agregadas
    technical_skills_score,
    total_skills_count,
    tech_stack_category,
    cloud_preference,
    is_premium_job,
    required_experience_years,
    
    -- Benefícios
    has_meal_voucher,
    has_health_insurance,
    has_dental,
    has_transport_voucher,
    has_flexible_hours,
    has_profit_sharing,
    
    -- Flags de qualidade
    is_valid_job
    
  FROM enriched_jobs
)

SELECT * FROM final
