# Data Jobs Pipeline

Pipeline completo de engenharia de dados para coleta, processamento e análise de vagas de emprego para Engenheiro de Dados.

## Objetivo

Construir um pipeline de dados moderno que:
1. Faça scraping de vagas de Engenheiro de Dados de diferentes fontes
2. Armazene os dados crus em PostgreSQL
3. Use DBT para transformar e modelar os dados
4. Orquestre tudo com Apache Airflow
5. Disponibilize dados prontos para análise em dashboards

## Arquitetura

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│   Scrapers  │───▶│  PostgreSQL  │───▶│     DBT     │───▶│ Dashboard   │
│ (Python)    │    │   (Raw Data) │    │(Transform)  │    │ (Streamlit) │
└─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘
       ▲                                       ▲
       │                                       │
       └───────────────────────────────────────┘
                    Apache Airflow
                   (Orquestração)
```

## Estrutura do Projeto

```
data-jobs-pipeline/
├── airflow/
│   ├── dags/
│   │   └── jobs_pipeline.py
│   ├── docker-compose.yaml
│   └── requirements.txt
├── scraping/
│   ├── __init__.py
│   ├── base_scraper.py
│   ├── indeed_scraper.py
│   ├── gupy_scraper.py
│   ├── linkedin_scraper.py
│   └── database.py
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── staging/
│   │   │   └── stg_jobs.sql
│   │   ├── intermediate/
│   │   │   └── int_jobs.sql
│   │   └── marts/
│   │       └── fct_job_trends.sql
│   └── macros/
├── sql/
│   └── init_database.sql
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Como Executar

### 1. Pré-requisitos

- Python 3.10+
- Docker e Docker Compose
- Git
- 4GB+ de RAM disponível
- 10GB+ de espaço em disco

### 2. Configuração Rápida

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/data-jobs-pipeline.git
cd data-jobs-pipeline

# Execute o script de configuração automática
chmod +x scripts/setup.sh
./scripts/setup.sh

# Inicie todos os serviços
docker-compose up -d
```

### 3. Configuração Manual (alternativa)

```bash
# Copie e configure as variáveis de ambiente
cp env.example .env
# Edite o arquivo .env conforme necessário

# Crie diretórios necessários
mkdir -p airflow/logs airflow/plugins airflow/config notebooks data

# Configure permissões (Linux/Mac)
sudo chown -R 50000:0 airflow/logs airflow/plugins airflow/config

# Defina AIRFLOW_UID
echo "AIRFLOW_UID=$(id -u)" >> .env

# Inicialize o Airflow
docker-compose up airflow-init

# Inicie os serviços
docker-compose up -d
```

### 4. Executar Testes Iniciais

#### Opção 1: Script Automático (Recomendado)
```bash
# Execute o script completo de testes
./scripts/run_tests.sh
```

#### Opção 2: Testes Manuais
```bash
# Verificar status dos containers
docker-compose ps

# Testar scrapers Python
python scripts/test_scrapers.py

# Testar conexão com banco específico
docker-compose exec postgres psql -U airflow -d airflow -c "SELECT version();"
```

#### Opção 3: Testes Rápidos
```bash
# Apenas verificar se Docker está funcionando
docker-compose up -d postgres
docker-compose ps

# Teste básico de scraping (2 vagas)
python scripts/test_scrapers.py
```

### 5. Acessar Interfaces

- **Streamlit Dashboard**: http://localhost:8501 (Dashboard principal com visualizações interativas)
- **Airflow**: http://localhost:8080 (airflow/airflow)
- **PostgreSQL**: localhost:5432 (airflow/airflow)
- **PgAdmin**: http://localhost:5050 (admin@datajobs.com/admin)
- **Jupyter**: http://localhost:8888 (token: data-jobs-pipeline)

### 6. Executar Pipeline

#### Via Airflow (Recomendado)
1. Acesse http://localhost:8080
2. Ative a DAG `jobs_pipeline`
3. Execute manualmente ou aguarde execução às 6h diárias

#### Via Linha de Comando (Testes)
```bash
# Executar um scraper específico
python scripts/run_scrapers.py scrape --source indeed --limit 50

# Executar todos os scrapers
python scripts/run_scrapers.py all --limit 30

# Executar DBT manualmente
docker-compose exec dbt dbt run
docker-compose exec dbt dbt test
```

## Dashboard

O projeto inclui um **dashboard interativo desenvolvido em Streamlit** como interface principal para visualização dos dados.

### Funcionalidades do Dashboard Streamlit
- **Métricas em tempo real**: Total de vagas, empresas únicas, fontes ativas
- **Filtros interativos**: Por fonte, período, localização
- **Visualizações dinâmicas**:
  - Distribuição de vagas por fonte
  - Tendência diária de coleta
  - Top empresas contratando
  - Análise geográfica
  - Skills mais demandadas
  - Distribuição por senioridade
  - Score técnico das vagas

### Acesso ao Dashboard
- **URL**: http://localhost:8501
- **Atualização**: Dados atualizados automaticamente a cada 5 minutos
- **Export**: Possibilidade de baixar dados como CSV

### Dashboards Alternativos (Opcionais)
Se preferir usar outras ferramentas de BI, configure o Metabase ou Superset para conectar ao PostgreSQL:
- Host: localhost
- Port: 5432
- Database: airflow
- Username: airflow
- Password: airflow

## Tecnologias Utilizadas

- **Python 3.10+**: Linguagem principal
- **Apache Airflow 2.x**: Orquestração
- **PostgreSQL**: Banco de dados
- **DBT Core**: Transformação de dados
- **Streamlit**: Dashboard interativo e visualizações
- **Plotly**: Gráficos interativos
- **Docker**: Containerização
- **BeautifulSoup/Selenium**: Web scraping
- **Pandas**: Manipulação de dados

## Funcionalidades

### Scrapers
- **Indeed**: Coleta vagas usando requests + BeautifulSoup
- **Gupy**: API pública quando disponível
- **LinkedIn**: Scraping cuidadoso respeitando rate limits

### Dados Coletados
- Título da vaga
- Nome da empresa
- Localização
- Descrição completa
- Salário (quando disponível)
- Data de publicação
- Fonte dos dados
- Timestamp da coleta

### Transformações DBT
- **Staging**: Limpeza e padronização dos dados
- **Intermediate**: Extração de skills e categorização
- **Marts**: Agregações para análise (tendências, métricas)

### Visualizações Disponíveis no Dashboard Streamlit
- **Métricas principais**: Total de vagas, empresas únicas, fontes ativas, vagas com salário
- **Evolução temporal**: Tendência diária de coleta de vagas por fonte
- **Análise por fonte**: Distribuição de vagas por plataforma (Indeed, Gupy, LinkedIn)
- **Top empresas**: Ranking das empresas com mais vagas abertas
- **Distribuição geográfica**: Vagas por localização/estado
- **Skills técnicas**: Análise das tecnologias mais demandadas (Python, SQL, Big Data, etc.)
- **Níveis de senioridade**: Distribuição por júnior, pleno, sênior
- **Score técnico**: Histograma da pontuação técnica das vagas
- **Análise temporal**: Padrão de coleta por hora do dia
- **Exportação de dados**: Download dos dados filtrados em CSV

## Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

## Avisos Importantes

- Respeite os termos de uso dos sites ao fazer scraping
- Implemente delays apropriados entre requests
- Use proxies se necessário para evitar bloqueios
- Monitore os logs do Airflow regularmente
- Faça backup dos dados importantes

## Solução de Problemas

### Erro de Conexão com PostgreSQL
```bash
# Verifique se o container está rodando
docker-compose ps

# Reinicie os serviços se necessário
docker-compose restart postgres
```

### DBT não encontra modelos
```bash
# Verifique o arquivo profiles.yml
dbt debug

# Recompile os modelos
dbt compile
```

### Airflow DAG não aparece
- Verifique a sintaxe do arquivo Python
- Confirme que o arquivo está na pasta dags/
- Recarregue a página do Airflow UI
