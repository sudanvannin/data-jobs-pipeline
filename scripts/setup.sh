#!/bin/bash

# Script de configuração inicial do projeto Data Jobs Pipeline

set -e

echo "🚀 Configurando Data Jobs Pipeline..."

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não encontrado. Por favor, instale o Docker primeiro."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não encontrado. Por favor, instale o Docker Compose primeiro."
    exit 1
fi

# Criar arquivo .env se não existir
if [ ! -f .env ]; then
    echo "📝 Criando arquivo .env..."
    cp env.example .env
    echo "✅ Arquivo .env criado. Configure as variáveis conforme necessário."
fi

# Criar diretórios necessários
echo "📁 Criando diretórios..."
mkdir -p airflow/logs
mkdir -p airflow/plugins
mkdir -p airflow/config
mkdir -p notebooks
mkdir -p data

# Configurar permissões
echo "🔐 Configurando permissões..."
sudo chown -R 50000:0 airflow/logs
sudo chown -R 50000:0 airflow/plugins
sudo chown -R 50000:0 airflow/config

# Definir AIRFLOW_UID
export AIRFLOW_UID=$(id -u)
echo "AIRFLOW_UID=$AIRFLOW_UID" >> .env

# Inicializar banco de dados do Airflow
echo "🗄️  Inicializando banco de dados..."
docker-compose up airflow-init

echo "✅ Configuração concluída!"
echo ""
echo "Para iniciar o pipeline:"
echo "  docker-compose up -d"
echo ""
echo "Acessos:"
echo "  Airflow: http://localhost:8080 (airflow/airflow)"
echo "  PostgreSQL: localhost:5432 (airflow/airflow)"
echo "  Streamlit Dashboard: http://localhost:8501"
echo "  PgAdmin: http://localhost:5050 (admin@datajobs.com/admin)"
