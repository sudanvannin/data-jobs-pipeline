"""
Dashboard Streamlit para visualização de vagas de emprego
Data Jobs Pipeline
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import psycopg2
from sqlalchemy import create_engine
import os
from datetime import datetime, timedelta
import numpy as np

# Configuração da página
st.set_page_config(
    page_title="Data Jobs Pipeline Dashboard",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
.main-header {
    font-size: 3rem;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
}
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #1f77b4;
}
.sidebar-header {
    font-size: 1.5rem;
    color: #1f77b4;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

def get_database_connection():
    """Conecta ao PostgreSQL e retorna engine SQLAlchemy."""
    try:
        # Configurações do banco
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5432')
        database = os.getenv('POSTGRES_DB', 'airflow')
        username = os.getenv('POSTGRES_USER', 'airflow')
        password = os.getenv('POSTGRES_PASSWORD', 'airflow')
        
        connection_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        engine = create_engine(connection_string)
        
        return engine
    except Exception as e:
        st.error(f"Erro ao conectar com banco de dados: {str(e)}")
        return None

@st.cache_data(ttl=300)
def load_jobs_data():
    """Carrega dados das vagas do PostgreSQL."""
    # Criar conexão dentro da função cached para evitar pickle
    try:
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5432')
        database = os.getenv('POSTGRES_DB', 'airflow')
        username = os.getenv('POSTGRES_USER', 'airflow')
        password = os.getenv('POSTGRES_PASSWORD', 'airflow')
        
        connection_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        engine = create_engine(connection_string)
    except Exception as e:
        st.error(f"Erro ao conectar com banco de dados: {str(e)}")
        return pd.DataFrame()
    
    try:
        query = """
        SELECT 
            id,
            title_clean as title,
            company_clean as company,
            location_clean as location,
            state,
            seniority_level,
            work_mode,
            has_python,
            has_sql,
            has_bigdata,
            has_orchestration,
            has_dbt,
            has_aws,
            has_azure,
            has_gcp,
            has_streaming,
            has_containers,
            has_ml,
            has_visualization,
            technical_skills_score,
            salary,
            date_posted,
            source,
            scraped_at,
            url,
            processed_at
        FROM int_jobs
        ORDER BY scraped_at DESC
        """
        
        df = pd.read_sql(query, engine)
        
        # Converter datas
        df['scraped_at'] = pd.to_datetime(df['scraped_at'])
        df['date_posted'] = pd.to_datetime(df['date_posted'])
        if 'processed_at' in df.columns:
            df['processed_at'] = pd.to_datetime(df['processed_at'])
        
        # Adicionar coluna de data para agrupamento
        df['scraped_date'] = df['scraped_at'].dt.date
        
        return df
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_summary_stats(df):
    """Calcula estatísticas resumo."""
    if df.empty:
        return {}
    
    stats = {
        'total_vagas': len(df),
        'total_empresas': df['company'].nunique(),
        'total_fontes': df['source'].nunique(),
        'vagas_com_salario': df['salary'].notna().sum(),
        'ultima_coleta': df['scraped_at'].max(),
        'primeira_coleta': df['scraped_at'].min(),
        'vagas_hoje': len(df[df['scraped_date'] == datetime.now().date()]),
        'vagas_ontem': len(df[df['scraped_date'] == (datetime.now().date() - timedelta(days=1))])
    }
    
    return stats

def create_source_chart(df):
    """Cria gráfico de vagas por fonte."""
    source_counts = df['source'].value_counts()
    
    fig = px.pie(
        values=source_counts.values,
        names=source_counts.index,
        title="Distribuição de Vagas por Fonte",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    
    return fig

def create_daily_trend_chart(df):
    """Cria gráfico de tendência diária."""
    daily_counts = df.groupby(['scraped_date', 'source']).size().reset_index(name='count')
    
    fig = px.line(
        daily_counts,
        x='scraped_date',
        y='count',
        color='source',
        title='Tendência Diária de Coleta de Vagas',
        markers=True
    )
    
    fig.update_layout(
        xaxis_title="Data",
        yaxis_title="Número de Vagas",
        height=400
    )
    
    return fig

def create_company_chart(df, top_n=15):
    """Cria gráfico das top empresas."""
    company_counts = df['company'].value_counts().head(top_n)
    
    fig = px.bar(
        x=company_counts.values,
        y=company_counts.index,
        orientation='h',
        title=f'Top {top_n} Empresas com Mais Vagas',
        labels={'x': 'Número de Vagas', 'y': 'Empresa'}
    )
    
    fig.update_layout(height=500, yaxis={'categoryorder':'total ascending'})
    
    return fig

def create_location_chart(df):
    """Cria gráfico de vagas por localização."""
    # Extrair estado/cidade da localização
    df_location = df.copy()
    df_location['location_clean'] = df_location['location'].fillna('Não informado')
    
    location_counts = df_location['location_clean'].value_counts().head(10)
    
    fig = px.bar(
        x=location_counts.index,
        y=location_counts.values,
        title='Top 10 Localizações',
        labels={'x': 'Localização', 'y': 'Número de Vagas'}
    )
    
    fig.update_layout(height=400, xaxis_tickangle=-45)
    
    return fig

def create_hourly_chart(df):
    """Cria gráfico de coleta por hora."""
    df_hourly = df.copy()
    df_hourly['hour'] = df_hourly['scraped_at'].dt.hour
    
    hourly_counts = df_hourly['hour'].value_counts().sort_index()
    
    fig = px.bar(
        x=hourly_counts.index,
        y=hourly_counts.values,
        title='Vagas Coletadas por Hora do Dia',
        labels={'x': 'Hora', 'y': 'Número de Vagas'}
    )
    
    fig.update_layout(height=400)
    
    return fig

def create_skills_analysis_chart(df):
    """Cria gráfico de análise de skills."""
    if df.empty:
        return None
    
    # Skills columns
    skills_cols = [col for col in df.columns if col.startswith('has_')]
    
    if not skills_cols:
        return None
    
    skills_data = []
    for col in skills_cols:
        skill_name = col.replace('has_', '').replace('_', ' ').title()
        skill_count = df[col].sum()
        skill_pct = (skill_count / len(df)) * 100
        skills_data.append({
            'skill': skill_name,
            'count': skill_count,
            'percentage': skill_pct
        })
    
    skills_df = pd.DataFrame(skills_data).sort_values('count', ascending=True)
    
    fig = px.bar(
        skills_df,
        x='count',
        y='skill',
        orientation='h',
        title='Skills Mais Demandadas',
        labels={'count': 'Número de Vagas', 'skill': 'Skill'},
        text='count'
    )
    
    fig.update_traces(textposition='outside')
    fig.update_layout(height=600)
    
    return fig

def create_seniority_chart(df):
    """Cria gráfico de distribuição por senioridade."""
    if 'seniority_level' not in df.columns:
        return None
    
    seniority_counts = df['seniority_level'].value_counts()
    
    fig = px.pie(
        values=seniority_counts.values,
        names=seniority_counts.index,
        title='Distribuição por Nível de Senioridade',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    
    return fig

def create_technical_score_chart(df):
    """Cria gráfico de distribuição do score técnico."""
    if 'technical_skills_score' not in df.columns:
        return None
    
    fig = px.histogram(
        df,
        x='technical_skills_score',
        nbins=20,
        title='Distribuição do Score Técnico das Vagas',
        labels={'technical_skills_score': 'Score Técnico', 'count': 'Número de Vagas'}
    )
    
    fig.update_layout(height=400)
    
    return fig

# Interface principal
def main():
    # Header
    st.markdown('<h1 class="main-header">Data Jobs Pipeline Dashboard</h1>', unsafe_allow_html=True)
    
    # Carregar dados
    with st.spinner('Carregando dados do PostgreSQL...'):
        df = load_jobs_data()
    
    if df.empty:
        st.error("Nenhum dado encontrado. Verifique se o pipeline coletou vagas.")
        st.info("Execute o pipeline do Airflow para coletar vagas primeiro.")
        return
    
    # Sidebar com filtros
    st.sidebar.markdown('<h2 class="sidebar-header">Filtros</h2>', unsafe_allow_html=True)
    
    # Filtro por fonte
    sources = ['Todas'] + list(df['source'].unique())
    selected_source = st.sidebar.selectbox('Fonte:', sources)
    
    # Filtro por data
    date_range = st.sidebar.date_input(
        'Período:',
        value=(df['scraped_date'].min(), df['scraped_date'].max()),
        min_value=df['scraped_date'].min(),
        max_value=df['scraped_date'].max()
    )
    
    # Aplicar filtros
    df_filtered = df.copy()
    
    if selected_source != 'Todas':
        df_filtered = df_filtered[df_filtered['source'] == selected_source]
    
    if len(date_range) == 2:
        df_filtered = df_filtered[
            (df_filtered['scraped_date'] >= date_range[0]) & 
            (df_filtered['scraped_date'] <= date_range[1])
        ]
    
    # Métricas principais
    stats = get_summary_stats(df_filtered)
    
    st.markdown("## Métricas Principais")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total de Vagas",
            value=stats.get('total_vagas', 0),
            delta=f"+{stats.get('vagas_hoje', 0)} hoje"
        )
    
    with col2:
        st.metric(
            label="Empresas Únicas",
            value=stats.get('total_empresas', 0)
        )
    
    with col3:
        st.metric(
            label="Fontes Ativas",
            value=stats.get('total_fontes', 0)
        )
    
    with col4:
        st.metric(
            label="Vagas com Salário",
            value=stats.get('vagas_com_salario', 0),
            delta=f"{(stats.get('vagas_com_salario', 0) / stats.get('total_vagas', 1) * 100):.1f}%"
        )
    
    # Gráficos
    st.markdown("## Visualizações")
    
    # Primeira linha de gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        fig_source = create_source_chart(df_filtered)
        st.plotly_chart(fig_source, use_container_width=True)
    
    with col2:
        fig_daily = create_daily_trend_chart(df_filtered)
        st.plotly_chart(fig_daily, use_container_width=True)
    
    # Segunda linha de gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        fig_location = create_location_chart(df_filtered)
        st.plotly_chart(fig_location, use_container_width=True)
    
    with col2:
        fig_hourly = create_hourly_chart(df_filtered)
        st.plotly_chart(fig_hourly, use_container_width=True)
    
    # Terceira linha - Skills e Senioridade
    col1, col2 = st.columns(2)
    
    with col1:
        fig_seniority = create_seniority_chart(df_filtered)
        if fig_seniority:
            st.plotly_chart(fig_seniority, use_container_width=True)
    
    with col2:
        fig_score = create_technical_score_chart(df_filtered)
        if fig_score:
            st.plotly_chart(fig_score, use_container_width=True)
    
    # Análise de Skills (largura total)
    st.markdown("### Análise de Skills Técnicas")
    fig_skills = create_skills_analysis_chart(df_filtered)
    if fig_skills:
        st.plotly_chart(fig_skills, use_container_width=True)
    
    # Gráfico das empresas (largura total)
    st.markdown("### Top Empresas")
    fig_companies = create_company_chart(df_filtered)
    st.plotly_chart(fig_companies, use_container_width=True)
    
    # Tabela de dados
    st.markdown("## Dados Detalhados")
    
    # Opções de exibição
    available_columns = ['title', 'company', 'location', 'state', 'seniority_level', 'work_mode', 
                        'source', 'scraped_at', 'salary', 'technical_skills_score', 'url']
    
    show_columns = st.multiselect(
        'Selecione as colunas para exibir:',
        options=available_columns,
        default=['title', 'company', 'location', 'state', 'seniority_level', 'source', 'technical_skills_score']
    )
    
    if show_columns:
        # Preparar dados para exibição
        display_df = df_filtered[show_columns].copy()
        
        # Formatar datas
        if 'scraped_at' in display_df.columns:
            display_df['scraped_at'] = display_df['scraped_at'].dt.strftime('%d/%m/%Y %H:%M')
        
        # Limitar URLs
        if 'url' in display_df.columns:
            display_df['url'] = display_df['url'].apply(
                lambda x: f"{x[:50]}..." if pd.notna(x) and len(str(x)) > 50 else x
            )
        
        st.dataframe(
            display_df,
            use_container_width=True,
            height=400
        )
        
        # Botão de download
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="Baixar dados como CSV",
            data=csv,
            file_name=f"vagas_data_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Informações do sistema
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Informações")
    if stats:
        st.sidebar.info(f"""
        **Última coleta:** {stats.get('ultima_coleta', 'N/A')}
        
        **Primeira coleta:** {stats.get('primeira_coleta', 'N/A')}
        
        **Total no banco:** {len(df)} vagas
        """)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "**Data Jobs Pipeline Dashboard** | "
        "Desenvolvido com Streamlit + PostgreSQL + Airflow"
    )

if __name__ == "__main__":
    main()
