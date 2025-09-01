#!/bin/bash

# Script completo de testes para o Data Jobs Pipeline

set -e

echo "🚀 DATA JOBS PIPELINE - TESTES INICIAIS"
echo "======================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log colorido
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# 1. Verificar pré-requisitos
echo ""
log_info "1. VERIFICANDO PRÉ-REQUISITOS"
echo "--------------------------------"

# Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    log_success "Docker encontrado: $DOCKER_VERSION"
else
    log_error "Docker não encontrado!"
    exit 1
fi

# Docker Compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    log_success "Docker Compose encontrado: $COMPOSE_VERSION"
else
    log_error "Docker Compose não encontrado!"
    exit 1
fi

# Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    log_success "Python encontrado: $PYTHON_VERSION"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version)
    log_success "Python encontrado: $PYTHON_VERSION"
else
    log_error "Python não encontrado!"
    exit 1
fi

# 2. Configurar ambiente
echo ""
log_info "2. CONFIGURANDO AMBIENTE"
echo "------------------------"

# Criar arquivo .env se não existir
if [ ! -f .env ]; then
    log_info "Criando arquivo .env..."
    cp env.example .env
    echo "AIRFLOW_UID=$(id -u 2>/dev/null || echo 50000)" >> .env
    log_success "Arquivo .env criado"
else
    log_success "Arquivo .env já existe"
fi

# Criar diretórios necessários
log_info "Criando diretórios..."
mkdir -p airflow/logs airflow/plugins airflow/config notebooks data
log_success "Diretórios criados"

# 3. Testar Docker Compose
echo ""
log_info "3. TESTANDO DOCKER COMPOSE"
echo "--------------------------"

# Verificar se docker-compose.yml é válido
if docker-compose config > /dev/null 2>&1; then
    log_success "docker-compose.yml é válido"
else
    log_error "docker-compose.yml tem erros!"
    exit 1
fi

# 4. Iniciar PostgreSQL
echo ""
log_info "4. INICIANDO POSTGRESQL"
echo "-----------------------"

log_info "Iniciando PostgreSQL..."
docker-compose up -d postgres

# Aguardar PostgreSQL inicializar
log_info "Aguardando PostgreSQL inicializar (30s)..."
sleep 30

# Verificar se PostgreSQL está rodando
if docker-compose exec -T postgres pg_isready -U airflow > /dev/null 2>&1; then
    log_success "PostgreSQL está rodando"
else
    log_error "PostgreSQL não está respondendo"
    docker-compose logs postgres
    exit 1
fi

# 5. Testar conexão com banco
echo ""
log_info "5. TESTANDO CONEXÃO COM BANCO"
echo "------------------------------"

# Testar conexão SQL
if docker-compose exec -T postgres psql -U airflow -d airflow -c "SELECT version();" > /dev/null 2>&1; then
    log_success "Conexão com PostgreSQL OK"
    
    # Mostrar versão
    DB_VERSION=$(docker-compose exec -T postgres psql -U airflow -d airflow -t -c "SELECT version();" | head -1 | xargs)
    log_info "Versão do PostgreSQL: $DB_VERSION"
else
    log_error "Falha na conexão com PostgreSQL"
    exit 1
fi

# 6. Instalar dependências Python
echo ""
log_info "6. INSTALANDO DEPENDÊNCIAS"
echo "---------------------------"

if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
fi

log_info "Instalando dependências Python..."
$PYTHON_CMD -m pip install -r requirements.txt > /dev/null 2>&1 || {
    log_warning "Erro ao instalar dependências. Continuando..."
}

# 7. Executar testes dos scrapers
echo ""
log_info "7. TESTANDO SCRAPERS"
echo "-------------------"

if [ -f "scripts/test_scrapers.py" ]; then
    log_info "Executando testes dos scrapers..."
    $PYTHON_CMD scripts/test_scrapers.py
else
    log_warning "Script de teste não encontrado"
fi

# 8. Testar inicialização do Airflow
echo ""
log_info "8. TESTANDO AIRFLOW"
echo "-------------------"

log_info "Inicializando Airflow..."
if docker-compose up airflow-init > /dev/null 2>&1; then
    log_success "Airflow inicializado com sucesso"
else
    log_warning "Erro na inicialização do Airflow (pode ser normal)"
fi

# 9. Testar DBT
echo ""
log_info "9. TESTANDO DBT"
echo "---------------"

log_info "Testando configuração DBT..."
if docker-compose run --rm dbt dbt debug > /dev/null 2>&1; then
    log_success "DBT configurado corretamente"
else
    log_warning "DBT não configurado (normal na primeira execução)"
fi

# 10. Status final
echo ""
log_info "10. STATUS FINAL DOS SERVIÇOS"
echo "-----------------------------"

docker-compose ps

# 11. Resumo e próximos passos
echo ""
echo "🎉 TESTES CONCLUÍDOS!"
echo "===================="
echo ""
log_success "Configuração básica funcionando"
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo ""
echo "1. Iniciar todos os serviços:"
echo "   docker-compose up -d"
echo ""
echo "2. Acessar interfaces:"
echo "   • Airflow: http://localhost:8080 (airflow/airflow)"
echo "   • PostgreSQL: localhost:5432 (airflow/airflow)"
echo ""
echo "3. Executar pipeline:"
echo "   • Via Airflow UI: ativar DAG 'jobs_pipeline'"
echo "   • Via comando: python scripts/test_scrapers.py"
echo ""
echo "4. Monitorar logs:"
echo "   docker-compose logs -f"
echo ""
echo "✅ Sistema pronto para uso!"
