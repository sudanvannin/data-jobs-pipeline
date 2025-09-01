"""
DAG principal do pipeline de coleta e processamento de vagas de emprego.
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List

from airflow import DAG
from airflow.decorators import task
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.postgres.operators.postgres import PostgresOperator
import pendulum

# Adicionar o diretório do projeto ao path para imports
sys.path.append('/opt/airflow/scraping')

# Configurações
DEFAULT_ARGS = {
    'owner': 'data-engineering-team',
    'depends_on_past': False,
    'start_date': pendulum.today('UTC').add(days=-1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'catchup': False
}

# Configuração da DAG
dag = DAG(
    'jobs_pipeline',
    default_args=DEFAULT_ARGS,
    description='Pipeline completo de coleta e processamento de vagas de emprego',
    schedule='0 6 * * *',  # Executa diariamente às 6h
    max_active_runs=1,
    tags=['data-engineering', 'scraping', 'jobs', 'etl']
)

# Configurações dos scrapers
SCRAPER_CONFIG = {
    'indeed': {
        'query': 'engenheiro de dados',
        'location': 'Brasil',
        'limit': 100
    },
    'gupy': {
        'query': 'engenheiro de dados',
        'location': 'Brasil', 
        'limit': 100
    },
    'linkedin': {
        'query': 'engenheiro de dados',
        'location': 'Brasil',
        'limit': 50  # LinkedIn tem rate limits mais restritivos
    }
}


def setup_logging():
    """Configura logging para as tarefas."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def log_scraper_execution(source: str, status: str, jobs_found: int = 0, 
                         jobs_inserted: int = 0, error_message: str = None):
    """
    Registra execução do scraper na tabela de logs.
    
    Args:
        source: Nome da fonte (indeed, gupy, linkedin)
        status: Status da execução (running, success, error, timeout)
        jobs_found: Número de vagas encontradas
        jobs_inserted: Número de vagas inseridas
        error_message: Mensagem de erro se houver
    """
    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    sql = """
    INSERT INTO scraper_logs 
    (source, status, jobs_found, jobs_inserted, error_message, end_time, execution_time_seconds)
    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 
            EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - 
            (SELECT start_time FROM scraper_logs 
             WHERE source = %s AND status = 'running' 
             ORDER BY start_time DESC LIMIT 1))))
    """
    
    postgres_hook.run(sql, parameters=(
        source, status, jobs_found, jobs_inserted, error_message, source
    ))


@task(task_id='initialize_database', dag=dag)
def initialize_database_task():
    """Inicializa o banco de dados e cria tabelas necessárias."""
    logger = setup_logging()
    
    try:
        from database import initialize_database
        
        logger.info("Inicializando banco de dados...")
        success = initialize_database()
        
        if success:
            logger.info("Banco de dados inicializado com sucesso")
            return {"status": "success", "message": "Database initialized"}
        else:
            raise Exception("Falha na inicialização do banco de dados")
            
    except Exception as e:
        logger.error(f"Erro na inicialização do banco: {str(e)}")
        raise


@task(task_id='scrape_indeed', dag=dag)
def scrape_indeed_task():
    """Executa scraping do Indeed."""
    logger = setup_logging()
    source = 'indeed'
    
    # Log início da execução
    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    postgres_hook.run(
        "INSERT INTO scraper_logs (source, status) VALUES (%s, %s)",
        parameters=(source, 'running')
    )
    
    try:
        from indeed_scraper import IndeedScraper
        from database import insert_scraped_jobs
        
        logger.info(f"Iniciando scraping do {source}...")
        
        config = SCRAPER_CONFIG[source]
        scraper = IndeedScraper(delay=2, max_retries=3)
        
        jobs = scraper.search_jobs(
            query=config['query'],
            location=config['location'],
            limit=config['limit']
        )
        
        jobs_found = len(jobs)
        logger.info(f"Encontradas {jobs_found} vagas no {source}")
        
        if jobs:
            jobs_inserted = insert_scraped_jobs(jobs, source)
            logger.info(f"Inseridas {jobs_inserted} vagas do {source}")
            
            log_scraper_execution(source, 'success', jobs_found, jobs_inserted)
            
            return {
                "status": "success",
                "source": source,
                "jobs_found": jobs_found,
                "jobs_inserted": jobs_inserted
            }
        else:
            log_scraper_execution(source, 'success', 0, 0)
            return {
                "status": "success",
                "source": source,
                "jobs_found": 0,
                "jobs_inserted": 0,
                "message": "Nenhuma vaga encontrada"
            }
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Erro no scraping do {source}: {error_msg}")
        log_scraper_execution(source, 'error', 0, 0, error_msg)
        raise


@task(task_id='scrape_gupy', dag=dag)
def scrape_gupy_task():
    """Executa scraping do Gupy."""
    logger = setup_logging()
    source = 'gupy'
    
    # Log início da execução
    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    postgres_hook.run(
        "INSERT INTO scraper_logs (source, status) VALUES (%s, %s)",
        parameters=(source, 'running')
    )
    
    try:
        from gupy_scraper import GupyScraper
        from database import insert_scraped_jobs
        
        logger.info(f"Iniciando scraping do {source}...")
        
        config = SCRAPER_CONFIG[source]
        scraper = GupyScraper(delay=2, max_retries=3)
        
        jobs = scraper.search_jobs(
            query=config['query'],
            location=config['location'],
            limit=config['limit']
        )
        
        jobs_found = len(jobs)
        logger.info(f"Encontradas {jobs_found} vagas no {source}")
        
        if jobs:
            jobs_inserted = insert_scraped_jobs(jobs, source)
            logger.info(f"Inseridas {jobs_inserted} vagas do {source}")
            
            log_scraper_execution(source, 'success', jobs_found, jobs_inserted)
            
            return {
                "status": "success",
                "source": source,
                "jobs_found": jobs_found,
                "jobs_inserted": jobs_inserted
            }
        else:
            log_scraper_execution(source, 'success', 0, 0)
            return {
                "status": "success",
                "source": source,
                "jobs_found": 0,
                "jobs_inserted": 0,
                "message": "Nenhuma vaga encontrada"
            }
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Erro no scraping do {source}: {error_msg}")
        log_scraper_execution(source, 'error', 0, 0, error_msg)
        raise


@task(task_id='scrape_linkedin', dag=dag)
def scrape_linkedin_task():
    """Executa scraping do LinkedIn."""
    logger = setup_logging()
    source = 'linkedin'
    
    # Log início da execução
    postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
    postgres_hook.run(
        "INSERT INTO scraper_logs (source, status) VALUES (%s, %s)",
        parameters=(source, 'running')
    )
    
    try:
        from linkedin_scraper import LinkedInScraper
        from database import insert_scraped_jobs
        
        logger.info(f"Iniciando scraping do {source}...")
        
        config = SCRAPER_CONFIG[source]
        scraper = LinkedInScraper(delay=3, max_retries=2)  # Mais conservador para LinkedIn
        
        jobs = scraper.search_jobs(
            query=config['query'],
            location=config['location'],
            limit=config['limit']
        )
        
        jobs_found = len(jobs)
        logger.info(f"Encontradas {jobs_found} vagas no {source}")
        
        if jobs:
            jobs_inserted = insert_scraped_jobs(jobs, source)
            logger.info(f"Inseridas {jobs_inserted} vagas do {source}")
            
            log_scraper_execution(source, 'success', jobs_found, jobs_inserted)
            
            return {
                "status": "success",
                "source": source,
                "jobs_found": jobs_found,
                "jobs_inserted": jobs_inserted
            }
        else:
            log_scraper_execution(source, 'success', 0, 0)
            return {
                "status": "success",
                "source": source,
                "jobs_found": 0,
                "jobs_inserted": 0,
                "message": "Nenhuma vaga encontrada"
            }
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Erro no scraping do {source}: {error_msg}")
        log_scraper_execution(source, 'error', 0, 0, error_msg)
        raise


@task(task_id='validate_scraped_data', dag=dag)
def validate_scraped_data_task():
    """
    Valida os dados coletados pelos scrapers.
    """
    logger = setup_logging()
    
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
        
        # Verificar se há dados novos
        today = datetime.now().date()
        
        # Verificar dados de todas as fontes
        sources = ['indeed', 'gupy', 'linkedin']
        
        for source in sources:
            # Verificar qualidade dos dados
            quality_sql = """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN title IS NULL OR TRIM(title) = '' THEN 1 END) as missing_title,
                COUNT(CASE WHEN company IS NULL OR TRIM(company) = '' THEN 1 END) as missing_company,
                COUNT(CASE WHEN description IS NULL OR TRIM(description) = '' THEN 1 END) as missing_description
            FROM raw_jobs 
            WHERE source = %s AND DATE(scraped_at) = %s
            """
            
            quality_result = postgres_hook.get_first(quality_sql, parameters=(source, today))
            
            if quality_result:
                total, missing_title, missing_company, missing_description = quality_result
                
                logger.info(f"Qualidade dos dados {source}:")
                logger.info(f"  Total: {total}")
                logger.info(f"  Títulos em branco: {missing_title}")
                logger.info(f"  Empresas em branco: {missing_company}")
                logger.info(f"  Descrições em branco: {missing_description}")
                
                # Alertar se qualidade estiver muito baixa
                if missing_title > total * 0.1:  # Mais de 10% sem título
                    logger.warning(f"Alta taxa de títulos em branco para {source}: {missing_title}/{total}")
        
        logger.info("Validação dos dados concluída")
        return {"status": "success", "message": "Data validation completed"}
        
    except Exception as e:
        logger.error(f"Erro na validação dos dados: {str(e)}")
        raise


@task(task_id='cleanup_old_data', dag=dag)
def cleanup_old_data_task():
    """Remove dados antigos do banco."""
    logger = setup_logging()
    
    try:
        postgres_hook = PostgresHook(postgres_conn_id='postgres_default')
        
        # Remover dados com mais de 90 dias
        cleanup_sql = "SELECT cleanup_old_data(90)"
        result = postgres_hook.get_first(cleanup_sql)
        
        deleted_count = result[0] if result else 0
        logger.info(f"Removidos {deleted_count} registros antigos")
        
        return {"status": "success", "deleted_records": deleted_count}
        
    except Exception as e:
        logger.error(f"Erro na limpeza de dados antigos: {str(e)}")
        raise


# Definir as tarefas
init_db = initialize_database_task()

# Tarefas de scraping (paralelas)
scrape_indeed = scrape_indeed_task()
scrape_gupy = scrape_gupy_task()
scrape_linkedin = scrape_linkedin_task()

# Validação dos dados coletados
validate_data = validate_scraped_data_task()

# Execução do DBT
dbt_run = BashOperator(
    task_id='dbt_run',
    bash_command='cd /opt/airflow/dbt && dbt run --profiles-dir /opt/airflow/dbt',
    dag=dag
)

dbt_test = BashOperator(
    task_id='dbt_test',
    bash_command='cd /opt/airflow/dbt && dbt test --profiles-dir /opt/airflow/dbt',
    dag=dag
)

# Limpeza de dados antigos
cleanup_data = cleanup_old_data_task()

# Atualização de estatísticas do banco
update_stats = PostgresOperator(
    task_id='update_database_stats',
    postgres_conn_id='postgres_default',
    sql="""
    ANALYZE raw_jobs;
    ANALYZE scraper_logs;
    
    -- Atualizar estatísticas customizadas se necessário
    REFRESH MATERIALIZED VIEW IF EXISTS mv_daily_stats;
    """,
    dag=dag
)

# Definir dependências
init_db >> [scrape_indeed, scrape_gupy, scrape_linkedin]
[scrape_indeed, scrape_gupy, scrape_linkedin] >> validate_data
validate_data >> dbt_run >> dbt_test
dbt_test >> [cleanup_data, update_stats]
