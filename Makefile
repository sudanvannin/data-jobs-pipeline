# Makefile para o Data Jobs Pipeline

.PHONY: help setup up down logs clean test scrape-test dbt-run dbt-test

# Variáveis
DOCKER_COMPOSE = docker-compose
PYTHON = python3

help: ## Mostrar ajuda
	@echo "Data Jobs Pipeline - Comandos disponíveis:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Configuração inicial do projeto
	@echo "🚀 Configurando Data Jobs Pipeline..."
	@chmod +x scripts/setup.sh
	@./scripts/setup.sh

up: ## Iniciar todos os serviços
	@echo "🔄 Iniciando serviços..."
	$(DOCKER_COMPOSE) up -d

down: ## Parar todos os serviços
	@echo "🛑 Parando serviços..."
	$(DOCKER_COMPOSE) down

restart: down up ## Reiniciar todos os serviços

logs: ## Mostrar logs dos serviços
	$(DOCKER_COMPOSE) logs -f

logs-airflow: ## Logs específicos do Airflow
	$(DOCKER_COMPOSE) logs -f airflow-webserver airflow-scheduler

status: ## Status dos containers
	$(DOCKER_COMPOSE) ps

clean: ## Limpar containers, volumes e imagens
	@echo "🧹 Limpando recursos Docker..."
	$(DOCKER_COMPOSE) down -v --rmi all
	docker system prune -f

# Testes e desenvolvimento
test-db: ## Testar conexão com banco de dados
	$(PYTHON) scripts/run_scrapers.py test-db

scrape-test: ## Executar teste de scraping (10 vagas de cada fonte)
	@echo "🕷️ Executando teste de scraping..."
	$(PYTHON) scripts/run_scrapers.py all --limit 10

scrape-indeed: ## Scraping apenas Indeed
	$(PYTHON) scripts/run_scrapers.py scrape --source indeed --limit 50

scrape-gupy: ## Scraping apenas Gupy
	$(PYTHON) scripts/run_scrapers.py scrape --source gupy --limit 50

scrape-linkedin: ## Scraping apenas LinkedIn
	$(PYTHON) scripts/run_scrapers.py scrape --source linkedin --limit 30

# DBT
dbt-deps: ## Instalar dependências DBT
	$(DOCKER_COMPOSE) exec dbt dbt deps

dbt-run: ## Executar modelos DBT
	$(DOCKER_COMPOSE) exec dbt dbt run

dbt-test: ## Executar testes DBT
	$(DOCKER_COMPOSE) exec dbt dbt test

dbt-docs: ## Gerar documentação DBT
	$(DOCKER_COMPOSE) exec dbt dbt docs generate
	$(DOCKER_COMPOSE) exec dbt dbt docs serve --port 8081

# Airflow
airflow-init: ## Inicializar Airflow
	$(DOCKER_COMPOSE) up airflow-init

# Banco de dados
db-shell: ## Conectar ao PostgreSQL
	$(DOCKER_COMPOSE) exec postgres psql -U airflow -d airflow

db-backup: ## Fazer backup do banco
	@echo "💾 Fazendo backup do banco..."
	$(DOCKER_COMPOSE) exec postgres pg_dump -U airflow airflow > backup_$(shell date +%Y%m%d_%H%M%S).sql

# Monitoramento
health-check: ## Verificar saúde dos serviços
	@echo "🏥 Verificando saúde dos serviços..."
	@curl -f http://localhost:8080/health || echo "❌ Airflow indisponível"
	@curl -f http://localhost:3000/api/health || echo "❌ Metabase indisponível"
	@$(DOCKER_COMPOSE) exec postgres pg_isready -U airflow || echo "❌ PostgreSQL indisponível"

# Desenvolvimento
dev-setup: ## Configuração para desenvolvimento
	@echo "👨‍💻 Configurando ambiente de desenvolvimento..."
	pip install -r requirements.txt
	pip install -r airflow/requirements.txt
	pre-commit install

lint: ## Executar linting do código
	black scraping/ scripts/
	flake8 scraping/ scripts/
	isort scraping/ scripts/

format: ## Formatar código
	black scraping/ scripts/
	isort scraping/ scripts/

# Jupyter
jupyter-start: ## Iniciar Jupyter Notebook
	$(DOCKER_COMPOSE) --profile jupyter up -d jupyter

jupyter-stop: ## Parar Jupyter Notebook
	$(DOCKER_COMPOSE) stop jupyter

# Dashboard
metabase-start: ## Iniciar apenas Metabase
	$(DOCKER_COMPOSE) --profile metabase up -d metabase

superset-start: ## Iniciar apenas Superset
	$(DOCKER_COMPOSE) --profile superset up -d superset

pgadmin-start: ## Iniciar PgAdmin
	$(DOCKER_COMPOSE) --profile pgadmin up -d pgadmin

# Produção
prod-up: ## Iniciar em modo produção
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down: ## Parar modo produção
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml down
