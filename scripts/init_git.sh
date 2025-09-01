#!/bin/bash

# Script para inicializar repositório Git do Data Jobs Pipeline

set -e

echo "🔧 Inicializando repositório Git..."

# Verificar se Git está instalado
if ! command -v git &> /dev/null; then
    echo "❌ Git não encontrado. Por favor, instale o Git primeiro."
    exit 1
fi

# Inicializar repositório se não existir
if [ ! -d ".git" ]; then
    echo "📁 Inicializando repositório Git..."
    git init
    
    # Configurar branch principal
    git branch -M main
    
    echo "✅ Repositório Git inicializado"
else
    echo "ℹ️  Repositório Git já existe"
fi

# Adicionar todos os arquivos
echo "📝 Adicionando arquivos ao Git..."
git add .

# Fazer commit inicial
if ! git diff --cached --quiet; then
    echo "💾 Fazendo commit inicial..."
    git commit -m "feat: Implementação inicial do Data Jobs Pipeline

- Pipeline completo de coleta de vagas de emprego
- Scrapers para Indeed, Gupy e LinkedIn  
- Processamento de dados com DBT
- Orquestração com Apache Airflow
- Containerização com Docker Compose
- Dashboards com Metabase/Superset
- Análise exploratória com Jupyter

Funcionalidades:
✅ Coleta automatizada de vagas
✅ Limpeza e padronização de dados
✅ Extração de skills e métricas
✅ Visualizações e dashboards
✅ Monitoramento e logs
✅ Configuração via Docker Compose"
    
    echo "✅ Commit inicial realizado"
else
    echo "ℹ️  Nenhuma alteração para commit"
fi

# Instruções para conectar ao GitHub
echo ""
echo "🚀 Próximos passos para publicar no GitHub:"
echo ""
echo "1. Crie um repositório no GitHub: https://github.com/new"
echo "2. Execute os comandos abaixo (substitua SEU_USUARIO e NOME_REPO):"
echo ""
echo "   git remote add origin https://github.com/SEU_USUARIO/NOME_REPO.git"
echo "   git push -u origin main"
echo ""
echo "3. Ou use SSH (recomendado):"
echo ""
echo "   git remote add origin git@github.com:SEU_USUARIO/NOME_REPO.git"
echo "   git push -u origin main"
echo ""
echo "📋 Exemplo completo:"
echo "   git remote add origin https://github.com/felipeuser/data-jobs-pipeline.git"
echo "   git push -u origin main"
echo ""
echo "✅ Repositório Git configurado e pronto para publicação!"
