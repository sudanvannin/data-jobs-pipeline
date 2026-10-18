#!/usr/bin/env python3
"""
CLI para executar os scrapers fora do Airflow.

Exemplos:
    python scripts/run_scrapers.py test-db
    python scripts/run_scrapers.py all --limit 10
    python scripts/run_scrapers.py scrape --source indeed --limit 50
"""

import argparse
import sys
from pathlib import Path

# Adicionar scraping ao path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "scraping"))

SOURCES = ["indeed", "gupy", "linkedin"]


def get_scraper(source: str):
    """Instancia o scraper da fonte informada."""
    if source == "indeed":
        from indeed_scraper import IndeedScraper
        return IndeedScraper()
    if source == "gupy":
        from gupy_scraper import GupyScraper
        return GupyScraper()
    if source == "linkedin":
        from linkedin_scraper import LinkedInScraper
        return LinkedInScraper()
    raise ValueError(f"Fonte desconhecida: {source}")


def test_db() -> int:
    """Testa a conexão com o PostgreSQL."""
    from database import get_database_manager

    db = get_database_manager()
    if db.test_connection():
        print("✅ Conexão com PostgreSQL OK")
        return 0
    print("❌ Falha na conexão com PostgreSQL")
    return 1


def scrape(source: str, query: str, location: str, limit: int) -> int:
    """Executa um scraper e grava as vagas no banco."""
    from database import get_database_manager

    scraper = get_scraper(source)
    print(f"🕷️ {source}: buscando até {limit} vagas para '{query}' em {location}...")
    jobs = scraper.search_jobs(query=query, location=location, limit=limit)
    print(f"   {len(jobs)} vagas encontradas")

    db = get_database_manager()
    db.create_raw_jobs_table()
    inserted = db.insert_jobs(jobs)
    print(f"   {inserted} vagas inseridas")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa os scrapers de vagas")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("test-db", help="Testa a conexão com o banco")

    scrape_parser = subparsers.add_parser("scrape", help="Executa uma fonte")
    scrape_parser.add_argument("--source", choices=SOURCES, required=True)

    all_parser = subparsers.add_parser("all", help="Executa todas as fontes")

    for p in (scrape_parser, all_parser):
        p.add_argument("--query", default="engenheiro de dados")
        p.add_argument("--location", default="Brasil")
        p.add_argument("--limit", type=int, default=50)

    args = parser.parse_args()

    if args.command == "test-db":
        return test_db()
    if args.command == "scrape":
        return scrape(args.source, args.query, args.location, args.limit)

    status = 0
    for source in SOURCES:
        try:
            scrape(source, args.query, args.location, args.limit)
        except Exception as e:
            print(f"❌ {source}: {e}")
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
