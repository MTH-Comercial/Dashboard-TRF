import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração e Identidade Visual
st.set_page_config(page_title="Painel Transforma | Mothé Engenharia", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    .main {background-color: #0E1117;}
    h1, h2, h3 {color: #4DA8DA;}
    .stProgress > div > div > div > div {background-color: #4DA8DA;}
    </style>
    """, unsafe_allow_html=True)

# Topo com Logo e Título
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    try:
        st.image("Mothé Eng. Logo.png", width=80)
    except:
        st.write("⚡")
with col_titulo:
    st.title("Painel de Engenharia | Transforma")
    st.markdown("**Mothé Engenharia** - Gestão do Contrato e Acompanhamento Técnico")
st.divider()

# 2. Conectando com o Google Sheets
@st.cache_data(ttl=30)
def carregar_dados():
    SHEET_ID = "1LgXQeTJ4FK1h8VLGRWijU3oGaE_FNg5gBTuB6XhEiKI"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    df = pd.read_csv(url)
    
    # Tratando as datas (Lendo o padrão brasileiro DD/MM/YYYY)
    df['Data de Início'] = pd.to_datetime(df['Data de Início'], format='%d/%m/%Y', errors='coerce')
    df['Data da Visita'] = pd.to_datetime(df['Data da Visita'], format='%d/%m/%Y', errors='coerce')
    df['Previsão de Conclusão'] = pd.to_datetime(df['Previsão de Conclusão'], format='%d/%m/%Y', errors='coerce')
    return df

df = carregar_dados()

# 3. Sidebar (Menu Lateral)
with st.sidebar:
    try:
        st.image("Mothé Eng. Cartão 2.png", use_column_width=True)
    except:
        st.write("Mothé Engenharia")
    st.header("⚙️ Filtros")
    base_selecionada = st.multiselect("Filtrar Base:", options=df["Base"].dropna().unique(), default=df["Base"].dropna().unique())
    status_selecionado = st.multiselect("Filtrar Status:", options=df["Status"].dropna().unique(), default=df["Status"].dropna().unique())

df_filtrado = df.query("Base in @base_selecionada and Status in @status_selecionado").copy()

# 4. Gestão do Contrato (O Cálculo Perfeito das Visitas)
st.subheader("📊 Cumprimento do Contrato Anual (Visitas Físicas)")
col_meta1, col_meta2 = st.columns(2)

# Filtra apenas linhas que têm 'Data da Visita' preenchida e conta os dias únicos (nunique)
df_visitas = df.dropna(subset=['Data da Visita'])
visitas_macae = df_visitas[df_visitas['Base'].str.contains('Macaé', na=False)]['Data da Visita'].nunique()
visitas_inter = df_visitas[~df_visitas['Base'].str.contains('Macaé', na=False)]['Data da Visita'].nunique()

with col_meta1:
    st.metric("Visitas Macaé (Meta: 104/ano)", f"{visitas_macae} realizadas")
    progresso_macae = min(visitas_macae / 104, 1.0)
    st.progress(progresso_macae)

with col_meta2:
    st.metric("Visitas Gradim/Açu (Meta: 12/ano)", f"{visitas_inter} realizadas")
    progresso_inter = min(visitas_inter / 12, 1.0)
    st.progress(progresso_inter)

st.divider()

# 5. Painel de Atividades (Indicadores de Topo)
col1, col2, col3, col4 = st.columns(4)
emergenciais = len(df_filtrado[df_filtrado["Prioridade"] == "Emergencial"])
concluidas = len(df_filtrado[df_filtrado["Status"] == "Resolvido"])
em_andamento = len(df_filtrado[df_filtrado["Status"] == "Em Andamento"])
pausadas = len(df_filtrado[df_filtrado["Status"].isin(["Pausado", "Aguardando Terceiro/Compras"])])

col1.metric("🚨 Atendimentos Emergenciais", emergenciais)
col2.metric("✅ Projetos Concluídos", concluidas)
col3.metric("⏳ Em Andamento", em_andamento)
col4.metric("⏸️ Pausados/Aguardando", pausadas)
st.divider()

# 6. Preparando os Dados para Exibição Bonita
# Regra de Porcentagem baseada na Fase (Sem precisar digitar na planilha)
def calcular_progresso(fase):
    fase = str(fase).strip()
    if fase == "Levantamento em Campo": return 25
    if fase == "Engenharia de Escritório": return 50
    if fase in ["Em Aprovação (Cliente)", "Aguardando Terceiros"]: return 65
    if fase == "Em Execução": return 85
    if fase == "Concluído": return 100
    return 0

df_filtrado['Progresso'] = df_filtrado['Fase'].apply(calcular_progresso)

# Formatando as datas para o padrão brasileiro e tratando as vazias ("Contínuo / A definir")
df_filtrado['Data de Início'] = df_filtrado['Data de Início'].dt.strftime('%d/%m/%Y').fillna('-')
df_filtrado['Data da Visita'] = df_filtrado['Data da Visita'].dt.strftime('%d/%m/%Y').fillna('Remoto/Escritório')
df_filtrado['Previsão de Conclusão'] = df_filtrado['Previsão de Conclusão'].dt.strftime('%d/%m/%Y').fillna('Contínuo / A definir')

# Separando Tabela Principal (Histórico/Execução) da Tabela de Futuro
df_futuro = df_filtrado[df_filtrado["Prioridade"] == "Planejamento (Futuro)"]
df_principal = df_filtrado[df_filtrado["Prioridade"] != "Planejamento (Futuro)"]

# 7. Tabela Principal com Barra de Progresso Visual
st.subheader("📋 Painel de Execução e Histórico")

# Configurando as colunas do Streamlit para gerar a barrinha animada
st.dataframe(
    df_principal[["Data de Início", "Data da Visita", "Base", "Categoria", "Descrição", "Fase", "Progresso", "Status", "Pendências/Observações"]],
    column_config={
        "Progresso": st.column_config.ProgressColumn("Progresso", help="Avanço baseado na fase do projeto", format="%d%%", min_value=0, max_value=100)
    },
    use_container_width=True,
    hide_index=True
)

st.divider()

# 8. Agenda Futura
st.subheader("📅 Próximos Passos (Planejamento Futuro)")
if df_futuro.empty:
    st.info("Nenhuma atividade futura agendada no momento.")
else:
    st.dataframe(df_futuro[["Data de Início", "Base", "Categoria", "Descrição", "Prioridade", "Status"]], use_container_width=True, hide_index=True)
