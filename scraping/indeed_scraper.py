"""
Scraper para vagas do Indeed.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

try:
    from .base_scraper import BaseScraper
except ImportError:
    from base_scraper import BaseScraper


class IndeedScraper(BaseScraper):
    """Scraper para coleta de vagas do Indeed."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://br.indeed.com"
        self.search_url = f"{self.base_url}/jobs"
        
    def get_source_name(self) -> str:
        """Retorna o nome da fonte."""
        return "indeed"
    
    def search_jobs(self, query: str = "engenheiro de dados", 
                   location: str = "Brasil", limit: int = 50) -> List[Dict]:
        """
        Busca vagas no Indeed.
        
        Args:
            query: Termo de busca
            location: Localização
            limit: Número máximo de vagas
            
        Returns:
            Lista de dicionários com dados das vagas
        """
        jobs = []
        start = 0
        page_size = 10  # Indeed mostra ~10 vagas por página
        
        while len(jobs) < limit:
            # Parâmetros da busca
            params = {
                'q': query,
                'l': location,
                'start': start,
                'limit': page_size
            }
            
            # Construir URL
            search_url = f"{self.search_url}?{urlencode(params)}"
            
            # Fazer requisição
            response = self.make_request(search_url)
            if not response:
                self.logger.error("Falha ao obter resposta do Indeed")
                break
                
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Encontrar vagas na página
            job_cards = soup.find_all('div', class_='job_seen_beacon')
            
            if not job_cards:
                self.logger.info("Nenhuma vaga encontrada na página atual")
                break
                
            # Processar cada vaga
            for card in job_cards:
                if len(jobs) >= limit:
                    break
                    
                job_data = self._parse_job_card(card)
                if job_data:
                    jobs.append(self.standardize_job_data(job_data))
                    
            # Próxima página
            start += page_size
            
            # Verificar se há mais páginas
            if len(job_cards) < page_size:
                break
                
        self.logger.info(f"Coletadas {len(jobs)} vagas do Indeed")
        return jobs
    
    def _parse_job_card(self, card) -> Optional[Dict]:
        """
        Extrai dados de um card de vaga.
        
        Args:
            card: Elemento BeautifulSoup do card da vaga
            
        Returns:
            Dicionário com dados da vaga ou None
        """
        try:
            # Título da vaga
            title_elem = card.find('h2', class_='jobTitle')
            if not title_elem:
                return None
                
            title_link = title_elem.find('a')
            if title_link:
                title = title_link.get('title') or title_link.get_text(strip=True)
                job_url = urljoin(self.base_url, title_link.get('href', ''))
            else:
                title = title_elem.get_text(strip=True)
                job_url = ""
            
            # Empresa
            company_elem = card.find('span', class_='companyName')
            company = company_elem.get_text(strip=True) if company_elem else ""
            
            # Localização
            location_elem = card.find('div', class_='companyLocation')
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Salário (se disponível)
            salary_elem = card.find('span', class_='salaryText')
            salary = salary_elem.get_text(strip=True) if salary_elem else None
            
            # Data de publicação
            date_elem = card.find('span', class_='date')
            date_posted = self._parse_date(date_elem.get_text(strip=True) if date_elem else "")
            
            # Descrição (snippet)
            desc_elem = card.find('div', class_='summary')
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # Se temos URL da vaga, tentar obter descrição completa
            if job_url and description:
                full_description = self._get_full_description(job_url)
                if full_description:
                    description = full_description
            
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
            self.logger.error(f"Erro ao processar card de vaga: {str(e)}")
            return None
    
    def _get_full_description(self, job_url: str) -> Optional[str]:
        """
        Obtém descrição completa da vaga.
        
        Args:
            job_url: URL da vaga
            
        Returns:
            Descrição completa ou None
        """
        try:
            response = self.make_request(job_url)
            if not response:
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Procurar pela descrição completa
            desc_elem = soup.find('div', class_='jobsearch-jobDescriptionText')
            if desc_elem:
                return desc_elem.get_text(strip=True, separator=' ')
                
        except Exception as e:
            self.logger.warning(f"Erro ao obter descrição completa: {str(e)}")
            
        return None
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """
        Converte texto de data para datetime.
        
        Args:
            date_text: Texto da data (ex: "há 3 dias", "hoje")
            
        Returns:
            Objeto datetime ou None
        """
        if not date_text:
            return None
            
        date_text = date_text.lower().strip()
        today = datetime.now().date()
        
        try:
            # Hoje
            if 'hoje' in date_text or 'agora' in date_text:
                return datetime.combine(today, datetime.min.time())
            
            # Ontem
            if 'ontem' in date_text:
                return datetime.combine(today - timedelta(days=1), datetime.min.time())
            
            # Há X dias
            days_match = re.search(r'há\s+(\d+)\s+dias?', date_text)
            if days_match:
                days_ago = int(days_match.group(1))
                return datetime.combine(today - timedelta(days=days_ago), datetime.min.time())
            
            # Há X semanas
            weeks_match = re.search(r'há\s+(\d+)\s+semanas?', date_text)
            if weeks_match:
                weeks_ago = int(weeks_match.group(1))
                return datetime.combine(today - timedelta(weeks=weeks_ago), datetime.min.time())
            
            # Há mais de X dias
            more_days_match = re.search(r'há\s+mais\s+de\s+(\d+)\s+dias?', date_text)
            if more_days_match:
                days_ago = int(more_days_match.group(1)) + 1  # Assumir +1 dia
                return datetime.combine(today - timedelta(days=days_ago), datetime.min.time())
                
        except Exception as e:
            self.logger.warning(f"Erro ao processar data '{date_text}': {str(e)}")
            
        return None
