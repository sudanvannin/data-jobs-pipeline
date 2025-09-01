"""
Módulo para interação com banco de dados PostgreSQL.
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


class DatabaseManager:
    """Gerenciador de conexão e operações com PostgreSQL."""
    
    def __init__(self, host: str = None, port: int = None, database: str = None,
                 username: str = None, password: str = None):
        """
        Inicializa o gerenciador de banco de dados.
        
        Args:
            host: Host do PostgreSQL
            port: Porta do PostgreSQL
            database: Nome do banco de dados
            username: Nome do usuário
            password: Senha do usuário
        """
        self.host = host or os.getenv('POSTGRES_HOST', 'localhost')
        self.port = port or int(os.getenv('POSTGRES_PORT', 5432))
        self.database = database or os.getenv('POSTGRES_DB', 'airflow')
        self.username = username or os.getenv('POSTGRES_USER', 'airflow')
        self.password = password or os.getenv('POSTGRES_PASSWORD', 'airflow')
        
        # String de conexão
        self.connection_string = (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )
        
        # Engine SQLAlchemy
        self.engine = create_engine(self.connection_string)
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
    def test_connection(self) -> bool:
        """
        Testa a conexão com o banco de dados.
        
        Returns:
            True se conexão bem-sucedida
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.logger.info("Conexão com banco de dados estabelecida com sucesso")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao conectar com banco de dados: {str(e)}")
            return False
    
    def create_raw_jobs_table(self) -> bool:
        """
        Cria a tabela raw_jobs se não existir.
        
        Returns:
            True se tabela foi criada ou já existe
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS raw_jobs (
            id SERIAL PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            company VARCHAR(300),
            location VARCHAR(300),
            description TEXT,
            salary VARCHAR(200),
            date_posted TIMESTAMP,
            source VARCHAR(50) NOT NULL,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Índices para melhor performance
        CREATE INDEX IF NOT EXISTS idx_raw_jobs_source ON raw_jobs(source);
        CREATE INDEX IF NOT EXISTS idx_raw_jobs_scraped_at ON raw_jobs(scraped_at);
        CREATE INDEX IF NOT EXISTS idx_raw_jobs_date_posted ON raw_jobs(date_posted);
        CREATE INDEX IF NOT EXISTS idx_raw_jobs_company ON raw_jobs(company);
        CREATE INDEX IF NOT EXISTS idx_raw_jobs_location ON raw_jobs(location);
        
        -- Trigger para atualizar updated_at
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        DROP TRIGGER IF EXISTS update_raw_jobs_updated_at ON raw_jobs;
        CREATE TRIGGER update_raw_jobs_updated_at
            BEFORE UPDATE ON raw_jobs
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
        
        try:
            with self.engine.begin() as conn:  # begin() faz commit automático
                conn.execute(text(create_table_sql))
            self.logger.info("Tabela raw_jobs criada/verificada com sucesso")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao criar tabela raw_jobs: {str(e)}")
            return False
    
    def insert_jobs(self, jobs: List[Dict]) -> int:
        """
        Insere vagas na tabela raw_jobs.
        
        Args:
            jobs: Lista de dicionários com dados das vagas
            
        Returns:
            Número de vagas inseridas
        """
        if not jobs:
            self.logger.warning("Lista de vagas vazia")
            return 0
        
        try:
            # Converter para DataFrame
            df = pd.DataFrame(jobs)
            
            # Garantir que as colunas existam
            required_columns = [
                'title', 'company', 'location', 'description', 
                'salary', 'date_posted', 'source', 'scraped_at', 'url'
            ]
            
            for col in required_columns:
                if col not in df.columns:
                    df[col] = None
            
            # Selecionar apenas as colunas necessárias
            df = df[required_columns]
            
            # Inserir no banco
            rows_inserted = df.to_sql(
                'raw_jobs',
                self.engine,
                if_exists='append',
                index=False,
                method='multi'
            )
            
            self.logger.info(f"{rows_inserted} vagas inseridas na tabela raw_jobs")
            return rows_inserted
            
        except Exception as e:
            self.logger.error(f"Erro ao inserir vagas: {str(e)}")
            return 0
    
    def get_jobs_count(self, source: Optional[str] = None, 
                      date_from: Optional[datetime] = None) -> int:
        """
        Obtém contagem de vagas.
        
        Args:
            source: Filtrar por fonte específica
            date_from: Filtrar vagas a partir desta data
            
        Returns:
            Número de vagas
        """
        try:
            query = "SELECT COUNT(*) as count FROM raw_jobs WHERE 1=1"
            params = {}
            
            if source:
                query += " AND source = :source"
                params['source'] = source
                
            if date_from:
                query += " AND scraped_at >= :date_from"
                params['date_from'] = date_from
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params)
                count = result.fetchone()[0]
                
            return count
            
        except Exception as e:
            self.logger.error(f"Erro ao obter contagem de vagas: {str(e)}")
            return 0
    
    def get_latest_jobs(self, limit: int = 10, source: Optional[str] = None) -> List[Dict]:
        """
        Obtém as vagas mais recentes.
        
        Args:
            limit: Número máximo de vagas
            source: Filtrar por fonte específica
            
        Returns:
            Lista de vagas
        """
        try:
            query = """
            SELECT id, title, company, location, salary, date_posted, source, scraped_at, url
            FROM raw_jobs 
            WHERE 1=1
            """
            params = {}
            
            if source:
                query += " AND source = :source"
                params['source'] = source
                
            query += " ORDER BY scraped_at DESC LIMIT :limit"
            params['limit'] = limit
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params)
                jobs = [dict(row._mapping) for row in result]
                
            return jobs
            
        except Exception as e:
            self.logger.error(f"Erro ao obter vagas recentes: {str(e)}")
            return []
    
    def delete_old_jobs(self, days_old: int = 90) -> int:
        """
        Remove vagas antigas do banco.
        
        Args:
            days_old: Número de dias para considerar vaga antiga
            
        Returns:
            Número de vagas removidas
        """
        try:
            query = """
            DELETE FROM raw_jobs 
            WHERE scraped_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
            """ % days_old
            
            with self.engine.begin() as conn:
                result = conn.execute(text(query))
                rows_deleted = result.rowcount
                
            self.logger.info(f"{rows_deleted} vagas antigas removidas")
            return rows_deleted
            
        except Exception as e:
            self.logger.error(f"Erro ao remover vagas antigas: {str(e)}")
            return 0
    
    def get_jobs_by_date_range(self, start_date: datetime, 
                              end_date: datetime) -> pd.DataFrame:
        """
        Obtém vagas por período.
        
        Args:
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            DataFrame com as vagas
        """
        try:
            query = """
            SELECT * FROM raw_jobs 
            WHERE scraped_at BETWEEN :start_date AND :end_date
            ORDER BY scraped_at DESC
            """
            
            df = pd.read_sql(
                query,
                self.engine,
                params={
                    'start_date': start_date,
                    'end_date': end_date
                }
            )
            
            return df
            
        except Exception as e:
            self.logger.error(f"Erro ao obter vagas por período: {str(e)}")
            return pd.DataFrame()
    
    def get_jobs_stats(self) -> Dict:
        """
        Obtém estatísticas das vagas.
        
        Returns:
            Dicionário com estatísticas
        """
        try:
            stats_query = """
            SELECT 
                COUNT(*) as total_jobs,
                COUNT(DISTINCT source) as total_sources,
                COUNT(DISTINCT company) as total_companies,
                COUNT(DISTINCT location) as total_locations,
                COUNT(CASE WHEN salary IS NOT NULL THEN 1 END) as jobs_with_salary,
                MIN(scraped_at) as first_scraped,
                MAX(scraped_at) as last_scraped
            FROM raw_jobs
            """
            
            source_stats_query = """
            SELECT source, COUNT(*) as count
            FROM raw_jobs
            GROUP BY source
            ORDER BY count DESC
            """
            
            with self.engine.connect() as conn:
                # Estatísticas gerais
                result = conn.execute(text(stats_query))
                general_stats = dict(result.fetchone()._mapping)
                
                # Estatísticas por fonte
                result = conn.execute(text(source_stats_query))
                source_stats = {row.source: row.count for row in result}
                
            return {
                'general': general_stats,
                'by_source': source_stats
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {}
    
    def close(self):
        """Fecha conexões com o banco."""
        if hasattr(self, 'engine'):
            self.engine.dispose()


def get_database_manager() -> DatabaseManager:
    """
    Factory function para criar instância do DatabaseManager.
    
    Returns:
        Instância configurada do DatabaseManager
    """
    return DatabaseManager()


def initialize_database() -> bool:
    """
    Inicializa o banco de dados criando tabelas necessárias.
    
    Returns:
        True se inicialização bem-sucedida
    """
    db = get_database_manager()
    
    try:
        # Testar conexão
        if not db.test_connection():
            return False
        
        # Criar tabela
        if not db.create_raw_jobs_table():
            return False
            
        return True
        
    finally:
        db.close()


def insert_scraped_jobs(jobs: List[Dict], source: str) -> int:
    """
    Função utilitária para inserir vagas coletadas.
    
    Args:
        jobs: Lista de vagas
        source: Nome da fonte
        
    Returns:
        Número de vagas inseridas
    """
    if not jobs:
        return 0
    
    # Garantir que todas as vagas têm a fonte correta
    for job in jobs:
        job['source'] = source
        if 'scraped_at' not in job or job['scraped_at'] is None:
            job['scraped_at'] = datetime.utcnow()
    
    db = get_database_manager()
    
    try:
        return db.insert_jobs(jobs)
    finally:
        db.close()
