"""
Scraper para vagas do Gupy.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

try:
    from .base_scraper import BaseScraper
except ImportError:
    from base_scraper import BaseScraper


class GupyScraper(BaseScraper):
    """Scraper para coleta de vagas do Gupy."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_base_url = "https://portal.api.gupy.io"
        self.search_endpoint = f"{self.api_base_url}/api/job"
        
    def get_source_name(self) -> str:
        """Retorna o nome da fonte."""
        return "gupy"
    
    def search_jobs(self, query: str = "engenheiro de dados", 
                   location: str = "Brasil", limit: int = 50) -> List[Dict]:
        """
        Busca vagas no Gupy usando a API pública.
        
        Args:
            query: Termo de busca
            location: Localização
            limit: Número máximo de vagas
            
        Returns:
            Lista de dicionários com dados das vagas
        """
        jobs = []
        offset = 0
        page_size = 20  # Tamanho padrão da página da API
        
        while len(jobs) < limit:
            # Parâmetros da API
            params = {
                'name': query,
                'city': location if location != "Brasil" else "",
                'offset': offset,
                'limit': min(page_size, limit - len(jobs))
            }
            
            # Headers específicos para API
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            # Fazer requisição para API
            response = self.make_request(self.search_endpoint, params=params, headers=headers)
            if not response:
                self.logger.error("Falha ao obter resposta da API do Gupy")
                break
            
            try:
                data = response.json()
                job_list = data.get('data', [])
                
                if not job_list:
                    self.logger.info("Nenhuma vaga encontrada na página atual")
                    break
                
                # Processar cada vaga
                for job_data in job_list:
                    if len(jobs) >= limit:
                        break
                        
                    processed_job = self._process_job_data(job_data)
                    if processed_job:
                        jobs.append(self.standardize_job_data(processed_job))
                
                # Verificar se há mais páginas
                if len(job_list) < page_size:
                    break
                    
                offset += page_size
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Erro ao decodificar JSON: {str(e)}")
                break
                
        self.logger.info(f"Coletadas {len(jobs)} vagas do Gupy")
        return jobs
    
    def _process_job_data(self, job_data: Dict) -> Optional[Dict]:
        """
        Processa dados de uma vaga da API do Gupy.
        
        Args:
            job_data: Dados brutos da vaga da API
            
        Returns:
            Dicionário com dados processados ou None
        """
        try:
            # Extrair informações básicas
            job_id = job_data.get('id')
            title = job_data.get('name', '')
            company = job_data.get('companyName', '')
            
            # Localização
            city = job_data.get('city', '')
            state = job_data.get('state', '')
            location = f"{city}, {state}" if city and state else city or state or ""
            
            # Tipo de trabalho
            work_type = job_data.get('type', '')
            if work_type:
                location = f"{location} ({work_type})" if location else work_type
            
            # Data de publicação
            published_date = job_data.get('publishedDate')
            date_posted = self._parse_api_date(published_date)
            
            # URL da vaga
            job_url = f"https://portal.gupy.io/job-details/{job_id}" if job_id else ""
            
            # Descrição (tentar obter da página da vaga)
            description = self._get_job_description(job_id) if job_id else ""
            
            # Salário (geralmente não disponível na API pública)
            salary = job_data.get('salary') or job_data.get('salaryRange')
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'description': description,
                'salary': salary,
                'date_posted': date_posted,
                'url': job_url
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao processar dados da vaga: {str(e)}")
            return None
    
    def _get_job_description(self, job_id: str) -> str:
        """
        Obtém descrição detalhada da vaga.
        
        Args:
            job_id: ID da vaga
            
        Returns:
            Descrição da vaga
        """
        try:
            # Endpoint para detalhes da vaga
            detail_url = f"{self.api_base_url}/api/job/{job_id}"
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            response = self.make_request(detail_url, headers=headers)
            if not response:
                return ""
            
            data = response.json()
            
            # Extrair descrição
            description_parts = []
            
            # Descrição principal
            main_desc = data.get('description', '')
            if main_desc:
                description_parts.append(main_desc)
            
            # Requisitos
            requirements = data.get('requirements', '')
            if requirements:
                description_parts.append(f"Requisitos: {requirements}")
            
            # Benefícios
            benefits = data.get('benefits', '')
            if benefits:
                description_parts.append(f"Benefícios: {benefits}")
            
            # Atividades
            activities = data.get('activities', '')
            if activities:
                description_parts.append(f"Atividades: {activities}")
            
            return " | ".join(description_parts)
            
        except Exception as e:
            self.logger.warning(f"Erro ao obter descrição da vaga {job_id}: {str(e)}")
            return ""
    
    def _parse_api_date(self, date_string: Optional[str]) -> Optional[datetime]:
        """
        Converte string de data da API para datetime.
        
        Args:
            date_string: String de data da API
            
        Returns:
            Objeto datetime ou None
        """
        if not date_string:
            return None
            
        try:
            # Formatos comuns da API Gupy
            date_formats = [
                '%Y-%m-%dT%H:%M:%S.%fZ',  # ISO format com microsegundos
                '%Y-%m-%dT%H:%M:%SZ',     # ISO format sem microsegundos
                '%Y-%m-%d %H:%M:%S',      # Formato padrão
                '%Y-%m-%d'                # Apenas data
            ]
            
            for date_format in date_formats:
                try:
                    return datetime.strptime(date_string, date_format)
                except ValueError:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Erro ao processar data '{date_string}': {str(e)}")
            
        return None
    
    def get_companies(self) -> List[Dict]:
        """
        Obtém lista de empresas disponíveis no Gupy.
        
        Returns:
            Lista de empresas
        """
        companies = []
        
        try:
            companies_url = f"{self.api_base_url}/api/companies"
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            response = self.make_request(companies_url, headers=headers)
            if response:
                data = response.json()
                companies = data.get('data', [])
                
        except Exception as e:
            self.logger.error(f"Erro ao obter empresas: {str(e)}")
            
        return companies
    
    def search_jobs_by_company(self, company_id: str, query: str = "engenheiro de dados", 
                              limit: int = 50) -> List[Dict]:
        """
        Busca vagas de uma empresa específica.
        
        Args:
            company_id: ID da empresa
            query: Termo de busca
            limit: Número máximo de vagas
            
        Returns:
            Lista de vagas da empresa
        """
        jobs = []
        
        try:
            params = {
                'companyId': company_id,
                'name': query,
                'limit': limit
            }
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            response = self.make_request(self.search_endpoint, params=params, headers=headers)
            if response:
                data = response.json()
                job_list = data.get('data', [])
                
                for job_data in job_list:
                    processed_job = self._process_job_data(job_data)
                    if processed_job:
                        jobs.append(self.standardize_job_data(processed_job))
                        
        except Exception as e:
            self.logger.error(f"Erro ao buscar vagas da empresa {company_id}: {str(e)}")
            
        return jobs
