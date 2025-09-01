{{
  config(
    materialized='view',
    description='Staging layer para dados de vagas - limpeza e padronização inicial'
  )
}}

WITH raw_data AS (
  SELECT 
    id,
    title,
    company,
    location,
    description,
    salary,
    date_posted,
    source,
    scraped_at,
    url,
    created_at,
    updated_at
  FROM raw_jobs
),

cleaned_data AS (
  SELECT 
    id,
    
    -- Limpeza e padronização do título
    TRIM(REGEXP_REPLACE(title, '\s+', ' ', 'g')) AS title_clean,
    LOWER(TRIM(REGEXP_REPLACE(title, '\s+', ' ', 'g'))) AS title_lower,
    
    -- Limpeza da empresa
    CASE 
      WHEN company IS NULL OR TRIM(company) = '' THEN 'Não informado'
      ELSE TRIM(REGEXP_REPLACE(company, '\s+', ' ', 'g'))
    END AS company_clean,
    
    -- Padronização da localização
    CASE 
      WHEN location IS NULL OR TRIM(location) = '' THEN 'Não informado'
      WHEN LOWER(location) LIKE '%remot%' OR LOWER(location) LIKE '%home office%' THEN 'Remoto'
      WHEN LOWER(location) LIKE '%híbrid%' OR LOWER(location) LIKE '%hibrid%' THEN 'Híbrido'
      ELSE TRIM(REGEXP_REPLACE(location, '\s+', ' ', 'g'))
    END AS location_clean,
    
    -- Extração do estado da localização
    CASE 
      WHEN LOWER(location) LIKE '%remot%' OR LOWER(location) LIKE '%home office%' THEN 'Remoto'
      WHEN LOWER(location) LIKE '%híbrid%' OR LOWER(location) LIKE '%hibrid%' THEN 'Híbrido'
      WHEN location ~ '.*,\s*(SP|São Paulo).*' THEN 'SP'
      WHEN location ~ '.*,\s*(RJ|Rio de Janeiro).*' THEN 'RJ'
      WHEN location ~ '.*,\s*(MG|Minas Gerais).*' THEN 'MG'
      WHEN location ~ '.*,\s*(PR|Paraná).*' THEN 'PR'
      WHEN location ~ '.*,\s*(SC|Santa Catarina).*' THEN 'SC'
      WHEN location ~ '.*,\s*(RS|Rio Grande do Sul).*' THEN 'RS'
      WHEN location ~ '.*,\s*(BA|Bahia).*' THEN 'BA'
      WHEN location ~ '.*,\s*(PE|Pernambuco).*' THEN 'PE'
      WHEN location ~ '.*,\s*(CE|Ceará).*' THEN 'CE'
      WHEN location ~ '.*,\s*(GO|Goiás).*' THEN 'GO'
      WHEN location ~ '.*,\s*(DF|Distrito Federal).*' THEN 'DF'
      ELSE 'Outros'
    END AS state,
    
    -- Limpeza da descrição
    TRIM(REGEXP_REPLACE(description, '\s+', ' ', 'g')) AS description_clean,
    LOWER(TRIM(REGEXP_REPLACE(description, '\s+', ' ', 'g'))) AS description_lower,
    
    -- Padronização do salário
    CASE 
      WHEN salary IS NULL OR TRIM(salary) = '' THEN NULL
      WHEN LOWER(salary) LIKE '%combinar%' OR LOWER(salary) LIKE '%negoci%' THEN NULL
      WHEN LOWER(salary) LIKE '%confidencial%' OR LOWER(salary) LIKE '%não informado%' THEN NULL
      ELSE TRIM(salary)
    END AS salary_clean,
    
    -- Extração de range salarial (valores numéricos)
    CASE 
      WHEN salary ~ '\d+' THEN 
        REGEXP_REPLACE(
          REGEXP_REPLACE(salary, '[^\d\-,.]', '', 'g'), 
          '\.(?=\d{1,2}$)', ',', 'g'
        )
      ELSE NULL
    END AS salary_numeric_text,
    
    -- Campos originais mantidos
    date_posted,
    source,
    scraped_at,
    url,
    created_at,
    updated_at,
    
    -- Flags de qualidade dos dados
    CASE 
      WHEN LENGTH(TRIM(title)) < {{ var('min_title_length') }} THEN FALSE
      WHEN LENGTH(TRIM(title)) > {{ var('max_title_length') }} THEN FALSE
      ELSE TRUE
    END AS is_title_valid,
    
    CASE 
      WHEN description IS NULL OR LENGTH(TRIM(description)) < {{ var('min_description_length') }} THEN FALSE
      ELSE TRUE
    END AS is_description_valid,
    
    -- Classificação de modalidade de trabalho
    CASE 
      WHEN LOWER(COALESCE(title, '') || ' ' || COALESCE(description, '') || ' ' || COALESCE(location, '')) 
           LIKE ANY(ARRAY['%remot%', '%home office%', '%trabalho em casa%']) THEN 'Remoto'
      WHEN LOWER(COALESCE(title, '') || ' ' || COALESCE(description, '') || ' ' || COALESCE(location, '')) 
           LIKE ANY(ARRAY['%híbrid%', '%hibrid%', '%flexível%']) THEN 'Híbrido'
      WHEN LOWER(COALESCE(title, '') || ' ' || COALESCE(description, '') || ' ' || COALESCE(location, '')) 
           LIKE ANY(ARRAY['%presencial%', '%on-site%', '%escritório%']) THEN 'Presencial'
      ELSE 'Não especificado'
    END AS work_mode,
    
    -- Identificação de nível de senioridade
    CASE 
      WHEN LOWER(title) LIKE ANY(ARRAY['%estagiár%', '%trainee%', '%aprendiz%']) THEN 'Estagiário'
      WHEN LOWER(title) LIKE ANY(ARRAY['%junior%', '%jr%', '%iniciante%']) THEN 'Junior'
      WHEN LOWER(title) LIKE ANY(ARRAY['%pleno%', '%pl%', '%mid%', '%middle%']) THEN 'Pleno'
      WHEN LOWER(title) LIKE ANY(ARRAY['%senior%', '%sr%', '%sênior%']) THEN 'Senior'
      WHEN LOWER(title) LIKE ANY(ARRAY['%especialista%', '%specialist%', '%expert%']) THEN 'Especialista'
      WHEN LOWER(title) LIKE ANY(ARRAY['%principal%', '%staff%', '%architect%']) THEN 'Principal'
      WHEN LOWER(title) LIKE ANY(ARRAY['%lead%', '%líder%', '%lider%', '%tech lead%']) THEN 'Lead'
      WHEN LOWER(title) LIKE ANY(ARRAY['%manager%', '%gerente%', '%head%']) THEN 'Manager'
      WHEN LOWER(title) LIKE ANY(ARRAY['%director%', '%diretor%', '%vp%']) THEN 'Director'
      ELSE 'Não especificado'
    END AS seniority_level
    
  FROM raw_data
),

final AS (
  SELECT 
    *,
    -- Criar hash único para detectar duplicatas
    MD5(
      COALESCE(title_lower, '') || '|' || 
      COALESCE(company_clean, '') || '|' || 
      COALESCE(location_clean, '') || '|' ||
      COALESCE(source, '')
    ) AS job_hash,
    
    -- Flag para vagas válidas (passa nos filtros de qualidade)
    CASE 
      WHEN is_title_valid AND is_description_valid THEN TRUE
      ELSE FALSE
    END AS is_valid_job
    
  FROM cleaned_data
)

SELECT * FROM final

-- Modelo de staging para jobs
