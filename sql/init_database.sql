-- Script de inicialização do banco de dados
-- Este script cria as tabelas e estruturas necessárias para o projeto

-- Criar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Criar schema para dados brutos se não existir
CREATE SCHEMA IF NOT EXISTS raw_data;

-- Criar schema para dados transformados se não existir  
CREATE SCHEMA IF NOT EXISTS analytics;

-- Tabela principal para armazenar vagas coletadas
CREATE TABLE IF NOT EXISTS raw_jobs (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    company VARCHAR(300),
    location VARCHAR(300),
    description TEXT,
    salary VARCHAR(200),
    date_posted TIMESTAMP,
    source VARCHAR(50) NOT NULL CHECK (source IN ('indeed', 'gupy', 'linkedin')),
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_title_not_empty CHECK (LENGTH(TRIM(title)) > 0),
    CONSTRAINT chk_source_not_empty CHECK (LENGTH(TRIM(source)) > 0)
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_raw_jobs_source ON raw_jobs(source);
CREATE INDEX IF NOT EXISTS idx_raw_jobs_scraped_at ON raw_jobs(scraped_at);
CREATE INDEX IF NOT EXISTS idx_raw_jobs_date_posted ON raw_jobs(date_posted);
CREATE INDEX IF NOT EXISTS idx_raw_jobs_company ON raw_jobs(company);
CREATE INDEX IF NOT EXISTS idx_raw_jobs_location ON raw_jobs(location);
CREATE INDEX IF NOT EXISTS idx_raw_jobs_title ON raw_jobs USING gin(to_tsvector('portuguese', title));
CREATE INDEX IF NOT EXISTS idx_raw_jobs_description ON raw_jobs USING gin(to_tsvector('portuguese', description));

-- Função para atualizar timestamp de updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para atualizar updated_at automaticamente
DROP TRIGGER IF EXISTS update_raw_jobs_updated_at ON raw_jobs;
CREATE TRIGGER update_raw_jobs_updated_at
    BEFORE UPDATE ON raw_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Tabela para logs de execução dos scrapers
CREATE TABLE IF NOT EXISTS scraper_logs (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running', 'success', 'error', 'timeout')),
    jobs_found INTEGER DEFAULT 0,
    jobs_inserted INTEGER DEFAULT 0,
    error_message TEXT,
    execution_time_seconds INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para tabela de logs
CREATE INDEX IF NOT EXISTS idx_scraper_logs_source ON scraper_logs(source);
CREATE INDEX IF NOT EXISTS idx_scraper_logs_start_time ON scraper_logs(start_time);
CREATE INDEX IF NOT EXISTS idx_scraper_logs_status ON scraper_logs(status);

-- Tabela para armazenar configurações do sistema
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger para system_config
DROP TRIGGER IF EXISTS update_system_config_updated_at ON system_config;
CREATE TRIGGER update_system_config_updated_at
    BEFORE UPDATE ON system_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Inserir configurações padrão
INSERT INTO system_config (config_key, config_value, description) VALUES
('scraping_delay', '2', 'Delay em segundos entre requests de scraping'),
('max_retries', '3', 'Número máximo de tentativas em caso de falha'),
('request_timeout', '30', 'Timeout para requests em segundos'),
('data_retention_days', '90', 'Dias para manter dados antigos'),
('daily_job_limit', '200', 'Limite de vagas por fonte por dia')
ON CONFLICT (config_key) DO NOTHING;

-- View para estatísticas rápidas
CREATE OR REPLACE VIEW jobs_stats AS
SELECT 
    source,
    COUNT(*) as total_jobs,
    COUNT(CASE WHEN salary IS NOT NULL THEN 1 END) as jobs_with_salary,
    COUNT(DISTINCT company) as unique_companies,
    COUNT(DISTINCT location) as unique_locations,
    MIN(date_posted) as oldest_job,
    MAX(date_posted) as newest_job,
    MIN(scraped_at) as first_scraped,
    MAX(scraped_at) as last_scraped
FROM raw_jobs
GROUP BY source;

-- View para vagas recentes (últimos 7 dias)
CREATE OR REPLACE VIEW recent_jobs AS
SELECT 
    id,
    title,
    company,
    location,
    salary,
    date_posted,
    source,
    scraped_at,
    url
FROM raw_jobs
WHERE scraped_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY scraped_at DESC;

-- View para tendências diárias
CREATE OR REPLACE VIEW daily_job_trends AS
SELECT 
    DATE(scraped_at) as scrape_date,
    source,
    COUNT(*) as jobs_count,
    COUNT(DISTINCT company) as companies_count,
    COUNT(CASE WHEN salary IS NOT NULL THEN 1 END) as jobs_with_salary
FROM raw_jobs
WHERE scraped_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY DATE(scraped_at), source
ORDER BY scrape_date DESC, source;

-- Função para limpeza de dados antigos
CREATE OR REPLACE FUNCTION cleanup_old_data(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM raw_jobs 
    WHERE scraped_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * retention_days;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Limpar logs antigos também
    DELETE FROM scraper_logs 
    WHERE start_time < CURRENT_TIMESTAMP - INTERVAL '1 day' * (retention_days * 2);
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Função para obter estatísticas de performance
CREATE OR REPLACE FUNCTION get_scraper_performance(days_back INTEGER DEFAULT 7)
RETURNS TABLE(
    source VARCHAR(50),
    executions BIGINT,
    avg_jobs_found NUMERIC,
    avg_jobs_inserted NUMERIC,
    avg_execution_time NUMERIC,
    success_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sl.source,
        COUNT(*) as executions,
        ROUND(AVG(sl.jobs_found), 2) as avg_jobs_found,
        ROUND(AVG(sl.jobs_inserted), 2) as avg_jobs_inserted,
        ROUND(AVG(sl.execution_time_seconds), 2) as avg_execution_time,
        ROUND(
            (COUNT(CASE WHEN sl.status = 'success' THEN 1 END)::NUMERIC / COUNT(*)) * 100, 
            2
        ) as success_rate
    FROM scraper_logs sl
    WHERE sl.start_time >= CURRENT_TIMESTAMP - INTERVAL '1 day' * days_back
    GROUP BY sl.source
    ORDER BY sl.source;
END;
$$ LANGUAGE plpgsql;

-- Comentários nas tabelas
COMMENT ON TABLE raw_jobs IS 'Tabela principal para armazenar vagas de emprego coletadas pelos scrapers';
COMMENT ON TABLE scraper_logs IS 'Logs de execução dos scrapers para monitoramento e debugging';
COMMENT ON TABLE system_config IS 'Configurações do sistema que podem ser alteradas sem restart';

COMMENT ON COLUMN raw_jobs.title IS 'Título da vaga de emprego';
COMMENT ON COLUMN raw_jobs.company IS 'Nome da empresa que oferece a vaga';
COMMENT ON COLUMN raw_jobs.location IS 'Localização da vaga (cidade, estado, remoto, etc.)';
COMMENT ON COLUMN raw_jobs.description IS 'Descrição completa da vaga';
COMMENT ON COLUMN raw_jobs.salary IS 'Informação salarial quando disponível';
COMMENT ON COLUMN raw_jobs.date_posted IS 'Data de publicação da vaga no site original';
COMMENT ON COLUMN raw_jobs.source IS 'Fonte da vaga (indeed, gupy, linkedin)';
COMMENT ON COLUMN raw_jobs.scraped_at IS 'Timestamp de quando a vaga foi coletada';
COMMENT ON COLUMN raw_jobs.url IS 'URL original da vaga';

-- Criar usuário para DBT se não existir (opcional)
-- DO $$
-- BEGIN
--     IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'dbt_user') THEN
--         CREATE USER dbt_user WITH PASSWORD 'dbt_password';
--         GRANT CONNECT ON DATABASE airflow TO dbt_user;
--         GRANT USAGE ON SCHEMA public TO dbt_user;
--         GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO dbt_user;
--         GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO dbt_user;
--         ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO dbt_user;
--         ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO dbt_user;
--     END IF;
-- END
-- $$;
