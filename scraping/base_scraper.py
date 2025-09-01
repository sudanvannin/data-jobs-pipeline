"""
Classe base para scrapers de vagas de emprego.
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
import requests

try:
    from fake_useragent import UserAgent
    HAS_FAKE_USERAGENT = True
except ImportError:
    HAS_FAKE_USERAGENT = False


class BaseScraper(ABC):
    """Classe base para todos os scrapers de vagas."""
    
    def __init__(self, delay: int = 2, max_retries: int = 3, timeout: int = 30):
        """
        Inicializa o scraper base.
        
        Args:
            delay: Tempo de espera entre requests (em segundos)
            max_retries: Número máximo de tentativas em caso de falha
            timeout: Timeout para requests (em segundos)
        """
        self.delay = delay
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = requests.Session()
        
        # Configurar User Agent
        if HAS_FAKE_USERAGENT:
            self.ua = UserAgent()
            user_agent = self.ua.random
        else:
            # User agent padrão se fake_useragent não estiver disponível
            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        
        # Configurar headers padrão
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Configurar logging
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    def get_source_name(self) -> str:
        """Retorna o nome da fonte (indeed, gupy, linkedin)."""
        pass
    
    @abstractmethod
    def search_jobs(self, query: str = "engenheiro de dados", 
                   location: str = "Brasil", limit: int = 50) -> List[Dict]:
        """
        Busca vagas de emprego.
        
        Args:
            query: Termo de busca
            location: Localização
            limit: Número máximo de vagas
            
        Returns:
            Lista de dicionários com dados das vagas
        """
        pass
    
    def make_request(self, url: str, params: Optional[Dict] = None, 
                    headers: Optional[Dict] = None) -> Optional[requests.Response]:
        """
        Faz uma requisição HTTP com retry e tratamento de erro.
        
        Args:
            url: URL para fazer a requisição
            params: Parâmetros da query string
            headers: Headers adicionais
            
        Returns:
            Response object ou None em caso de falha
        """
        if headers:
            session_headers = self.session.headers.copy()
            session_headers.update(headers)
        else:
            session_headers = self.session.headers
            
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Fazendo request para {url} (tentativa {attempt + 1})")
                
                response = self.session.get(
                    url,
                    params=params,
                    headers=session_headers,
                    timeout=self.timeout
                )
                
                # Verificar se a resposta foi bem-sucedida
                response.raise_for_status()
                
                # Delay entre requests
                if self.delay > 0:
                    time.sleep(self.delay)
                    
                return response
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Erro na tentativa {attempt + 1}: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    # Delay progressivo em caso de erro
                    wait_time = (attempt + 1) * 2
                    self.logger.info(f"Aguardando {wait_time}s antes da próxima tentativa...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Falha após {self.max_retries} tentativas para {url}")
                    
        return None
    
    def clean_text(self, text: Optional[str]) -> str:
        """
        Limpa e normaliza texto.
        
        Args:
            text: Texto para limpar
            
        Returns:
            Texto limpo
        """
        if not text:
            return ""
            
        # Remove espaços extras e quebras de linha
        cleaned = " ".join(text.strip().split())
        
        # Remove caracteres especiais problemáticos
        cleaned = cleaned.replace('\u00a0', ' ')  # Non-breaking space
        cleaned = cleaned.replace('\u200b', '')   # Zero-width space
        
        return cleaned
    
    def parse_salary(self, salary_text: Optional[str]) -> Optional[str]:
        """
        Extrai e padroniza informações de salário.
        
        Args:
            salary_text: Texto contendo informação salarial
            
        Returns:
            Salário padronizado ou None
        """
        if not salary_text:
            return None
            
        # Limpar texto
        salary_clean = self.clean_text(salary_text.lower())
        
        # Se contém "a combinar", "não informado", etc.
        if any(term in salary_clean for term in [
            'a combinar', 'não informado', 'confidencial', 
            'negociável', 'não especificado'
        ]):
            return None
            
        # Retornar texto original limpo se contém números
        if any(char.isdigit() for char in salary_clean):
            return self.clean_text(salary_text)
            
        return None
    
    def standardize_job_data(self, raw_data: Dict) -> Dict:
        """
        Padroniza dados de uma vaga para o formato padrão.
        
        Args:
            raw_data: Dados brutos da vaga
            
        Returns:
            Dados padronizados
        """
        return {
            'title': self.clean_text(raw_data.get('title', '')),
            'company': self.clean_text(raw_data.get('company', '')),
            'location': self.clean_text(raw_data.get('location', '')),
            'description': self.clean_text(raw_data.get('description', '')),
            'salary': self.parse_salary(raw_data.get('salary')),
            'date_posted': raw_data.get('date_posted'),
            'source': self.get_source_name(),
            'scraped_at': datetime.utcnow(),
            'url': raw_data.get('url', '')
        }
    
    def __del__(self):
        """Fecha a sessão ao destruir o objeto."""
        if hasattr(self, 'session'):
            self.session.close()
