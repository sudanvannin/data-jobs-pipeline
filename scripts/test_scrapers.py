#!/usr/bin/env python3
"""
Script para testar scrapers individualmente.
"""

import sys
import os
from pathlib import Path

# Adicionar scraping ao path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "scraping"))

def test_imports():
    """Testa se todos os imports estão funcionando."""
    print("🔍 Testando imports...")
    
    try:
        from base_scraper import BaseScraper
        print("✅ BaseScraper importado com sucesso")
        
        from indeed_scraper import IndeedScraper  
        print("✅ IndeedScraper importado com sucesso")
        
        from gupy_scraper import GupyScraper
        print("✅ GupyScraper importado com sucesso")
        
        from linkedin_scraper import LinkedInScraper
        print("✅ LinkedInScraper importado com sucesso")
        
        from database import DatabaseManager
        print("✅ DatabaseManager importado com sucesso")
        
        return True
        
    except ImportError as e:
        print(f"❌ Erro de import: {e}")
        return False

def test_scraper_creation():
    """Testa criação dos scrapers."""
    print("\n🏗️ Testando criação dos scrapers...")
    
    try:
        from indeed_scraper import IndeedScraper
        from gupy_scraper import GupyScraper
        from linkedin_scraper import LinkedInScraper
        
        # Testar Indeed
        indeed = IndeedScraper(delay=1, max_retries=1)
        print(f"✅ IndeedScraper criado - fonte: {indeed.get_source_name()}")
        
        # Testar Gupy
        gupy = GupyScraper(delay=1, max_retries=1)
        print(f"✅ GupyScraper criado - fonte: {gupy.get_source_name()}")
        
        # Testar LinkedIn
        linkedin = LinkedInScraper(delay=1, max_retries=1)
        print(f"✅ LinkedInScraper criado - fonte: {linkedin.get_source_name()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na criação: {e}")
        return False

def test_database_connection():
    """Testa conexão com banco de dados."""
    print("\n🗄️ Testando conexão com banco...")
    
    try:
        from database import get_database_manager
        
        db = get_database_manager()
        
        if db.test_connection():
            print("✅ Conexão com PostgreSQL OK")
            
            # Testar criação de tabela
            if db.create_raw_jobs_table():
                print("✅ Tabela raw_jobs criada/verificada")
                
                # Obter estatísticas
                stats = db.get_jobs_stats()
                if stats:
                    general = stats.get('general', {})
                    print(f"📊 Vagas no banco: {general.get('total_jobs', 0)}")
                
                return True
            else:
                print("❌ Erro ao criar tabela")
                return False
        else:
            print("❌ Falha na conexão com PostgreSQL")
            return False
            
    except Exception as e:
        print(f"❌ Erro de banco: {e}")
        print("💡 Certifique-se de que o PostgreSQL está rodando:")
        print("   docker-compose up -d postgres")
        return False

def test_simple_scraping():
    """Teste simples de scraping (apenas 2 vagas)."""
    print("\n🕷️ Testando scraping simples...")
    
    try:
        from indeed_scraper import IndeedScraper
        
        scraper = IndeedScraper(delay=1, max_retries=1)
        print("🔍 Buscando 2 vagas no Indeed...")
        
        jobs = scraper.search_jobs(
            query="engenheiro de dados",
            location="São Paulo",
            limit=2
        )
        
        if jobs:
            print(f"✅ Encontradas {len(jobs)} vagas!")
            
            for i, job in enumerate(jobs, 1):
                title = job.get('title', 'N/A')[:50]
                company = job.get('company', 'N/A')[:30]
                print(f"  {i}. {title} - {company}")
                
            return True
        else:
            print("⚠️ Nenhuma vaga encontrada (pode ser normal)")
            return True
            
    except Exception as e:
        print(f"❌ Erro no scraping: {e}")
        print("💡 Isso pode ser normal se houver rate limiting")
        return False

def main():
    """Executa todos os testes."""
    print("🚀 INICIANDO TESTES DO DATA JOBS PIPELINE")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Criação de Scrapers", test_scraper_creation),
        ("Conexão com Banco", test_database_connection),
        ("Scraping Simples", test_simple_scraping)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        results[test_name] = test_func()
    
    # Resumo
    print("\n" + "=" * 50)
    print("📋 RESUMO DOS TESTES")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results.items():
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Resultado: {passed}/{len(tests)} testes passaram")
    
    if passed == len(tests):
        print("🎉 Todos os testes passaram! O pipeline está pronto.")
    elif passed >= 2:
        print("⚠️ Alguns testes falharam, mas o básico está funcionando.")
    else:
        print("❌ Muitos testes falharam. Verifique a configuração.")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
