"""
Scraper para vagas do LinkedIn.
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


class LinkedInScraper(BaseScraper):
    """Scraper para coleta de vagas do LinkedIn."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://www.linkedin.com"
        self.jobs_url = f"{self.base_url}/jobs/search"
        
        # Headers específicos para LinkedIn
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Upgrade-Insecure-Requests': '1'
        })
        
    def get_source_name(self) -> str:
        """Retorna o nome da fonte."""
        return "linkedin"
    
    def search_jobs(self, query: str = "engenheiro de dados", 
                   location: str = "Brasil", limit: int = 50) -> List[Dict]:
        """
        Busca vagas no LinkedIn.
        
        Args:
            query: Termo de busca
            location: Localização
            limit: Número máximo de vagas
            
        Returns:
            Lista de dicionários com dados das vagas
        """
        jobs = []
        start = 0
        page_size = 25  # LinkedIn mostra 25 vagas por página
        
        while len(jobs) < limit:
            # Parâmetros da busca
            params = {
                'keywords': query,
                'location': location,
                'start': start,
                'f_TPR': 'r2592000',  # Últimos 30 dias
                'f_JT': 'F',          # Full-time
                'sortBy': 'DD'        # Ordenar por data
            }
            
            # Construir URL
            search_url = f"{self.jobs_url}?{urlencode(params)}"
            
            # Fazer requisição
            response = self.make_request(search_url)
            if not response:
                self.logger.error("Falha ao obter resposta do LinkedIn")
                break
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Encontrar vagas na página
            job_cards = soup.find_all('div', class_='base-card')
            
            if not job_cards:
                self.logger.info("Nenhuma vaga encontrada na página atual")
                # Tentar seletor alternativo
                job_cards = soup.find_all('li', class_='result-card')
                
            if not job_cards:
                self.logger.warning("Nenhum card de vaga encontrado - possível mudança na estrutura")
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
        
        self.logger.info(f"Coletadas {len(jobs)} vagas do LinkedIn")
        return jobs
    
    def _parse_job_card(self, card) -> Optional[Dict]:
        """
        Extrai dados de um card de vaga do LinkedIn.
        
        Args:
            card: Elemento BeautifulSoup do card da vaga
            
        Returns:
            Dicionário com dados da vaga ou None
        """
        try:
            # Título da vaga
            title_elem = (card.find('h3', class_='base-search-card__title') or 
                         card.find('h3', class_='result-card__title') or
                         card.find('a', class_='result-card__full-card-link'))
            
            if not title_elem:
                return None
            
            # Extrair título e URL
            if title_elem.name == 'a':
                title = title_elem.get_text(strip=True)
                job_url = title_elem.get('href', '')
            else:
                title_link = title_elem.find('a')
                if title_link:
                    title = title_link.get_text(strip=True)
                    job_url = title_link.get('href', '')
                else:
                    title = title_elem.get_text(strip=True)
                    job_url = ""
            
            # Limpar URL
            if job_url and not job_url.startswith('http'):
                job_url = urljoin(self.base_url, job_url)
            
            # Empresa
            company_elem = (card.find('h4', class_='base-search-card__subtitle') or
                           card.find('h4', class_='result-card__subtitle') or
                           card.find('a', {'data-tracking-control-name': 'public_jobs_jserp-result_job-search-card-subtitle'}))
            
            company = ""
            if company_elem:
                company_link = company_elem.find('a')
                company = (company_link.get_text(strip=True) if company_link 
                          else company_elem.get_text(strip=True))
            
            # Localização
            location_elem = (card.find('span', class_='job-search-card__location') or
                            card.find('span', class_='result-card__location'))
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Data de publicação
            time_elem = (card.find('time', class_='job-search-card__listdate') or
                        card.find('time', class_='result-card__listdate'))
            
            date_posted = None
            if time_elem:
                date_text = time_elem.get('datetime') or time_elem.get_text(strip=True)
                date_posted = self._parse_date(date_text)
            
            # Descrição (snippet se disponível)
            desc_elem = card.find('p', class_='job-search-card__snippet')
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # Tentar obter descrição completa se temos URL
            if job_url and not description:
                full_description = self._get_full_description(job_url)
                if full_description:
                    description = full_description
            
            return {
                'title': title,
                'company': company,
                'location': location,
                'description': description,
                'salary': None,  # LinkedIn raramente mostra salário publicamente
                'date_posted': date_posted,
                'url': job_url
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao processar card de vaga do LinkedIn: {str(e)}")
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
            # LinkedIn pode bloquear muitas requisições
            # Usar delay maior para páginas individuais
            original_delay = self.delay
            self.delay = max(3, self.delay)
            
            response = self.make_request(job_url)
            self.delay = original_delay  # Restaurar delay original
            
            if not response:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Procurar pela descrição completa
            desc_selectors = [
                'div.show-more-less-html__markup',
                'div.description__text',
                'section.description',
                'div.job-description'
            ]
            
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    return desc_elem.get_text(strip=True, separator=' ')
            
        except Exception as e:
            self.logger.warning(f"Erro ao obter descrição completa do LinkedIn: {str(e)}")
        
        return None
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """
        Converte texto de data do LinkedIn para datetime.
        
        Args:
            date_text: Texto da data
            
        Returns:
            Objeto datetime ou None
        """
        if not date_text:
            return None
        
        date_text = date_text.lower().strip()
        today = datetime.now().date()
        
        try:
            # Formato ISO (datetime attribute)
            if 'T' in date_text and 'Z' in date_text:
                return datetime.fromisoformat(date_text.replace('Z', '+00:00'))
            
            # Formato de data absoluta
            if re.match(r'\d{4}-\d{2}-\d{2}', date_text):
                return datetime.strptime(date_text[:10], '%Y-%m-%d')
            
            # Texto relativo em português
            if 'agora' in date_text or 'hoje' in date_text:
                return datetime.combine(today, datetime.min.time())
            
            if 'ontem' in date_text:
                return datetime.combine(today - timedelta(days=1), datetime.min.time())
            
            # Há X dias/semanas/meses
            time_patterns = [
                (r'há\s+(\d+)\s+dias?', 'days'),
                (r'há\s+(\d+)\s+semanas?', 'weeks'),
                (r'há\s+(\d+)\s+meses?', 'months'),
                (r'(\d+)\s+days?\s+ago', 'days'),
                (r'(\d+)\s+weeks?\s+ago', 'weeks'),
                (r'(\d+)\s+months?\s+ago', 'months')
            ]
            
            for pattern, unit in time_patterns:
                match = re.search(pattern, date_text)
                if match:
                    value = int(match.group(1))
                    
                    if unit == 'days':
                        target_date = today - timedelta(days=value)
                    elif unit == 'weeks':
                        target_date = today - timedelta(weeks=value)
                    elif unit == 'months':
                        # Aproximação: 1 mês = 30 dias
                        target_date = today - timedelta(days=value * 30)
                    
                    return datetime.combine(target_date, datetime.min.time())
            
        except Exception as e:
            self.logger.warning(f"Erro ao processar data do LinkedIn '{date_text}': {str(e)}")
        
        return None
    
    def login(self, email: str, password: str) -> bool:
        """
        Faz login no LinkedIn (opcional, para acesso a mais dados).
        
        Args:
            email: Email do LinkedIn
            password: Senha do LinkedIn
            
        Returns:
            True se login bem-sucedido
        """
        try:
            # Obter página de login
            login_url = f"{self.base_url}/login"
            response = self.make_request(login_url)
            
            if not response:
                return False
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Encontrar formulário de login
            login_form = soup.find('form', {'class': 'login__form'})
            if not login_form:
                self.logger.error("Formulário de login não encontrado")
                return False
            
            # Preparar dados do login
            login_data = {
                'session_key': email,
                'session_password': password
            }
            
            # Encontrar campos ocultos
            for hidden_input in login_form.find_all('input', type='hidden'):
                name = hidden_input.get('name')
                value = hidden_input.get('value', '')
                if name:
                    login_data[name] = value
            
            # Fazer login
            login_response = self.session.post(
                f"{self.base_url}/checkpoint/lg/login-submit",
                data=login_data,
                headers={'Referer': login_url}
            )
            
            # Verificar se login foi bem-sucedido
            if 'feed' in login_response.url or login_response.status_code == 200:
                self.logger.info("Login no LinkedIn realizado com sucesso")
                return True
            else:
                self.logger.error("Falha no login do LinkedIn")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro durante login no LinkedIn: {str(e)}")
            return False
