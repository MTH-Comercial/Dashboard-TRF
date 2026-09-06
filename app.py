import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração e Identidade Visual
st.set_page_config(page_title="Painel Transforma | Mothé Engenharia", layout="wide", page_icon="⚡")

# Cores: Azul Mothé (#4DA8DA) e Verde Transforma (#1B7543)
st.markdown("""
    <style>
    .main {background-color: #0E1117;}
    h1, h2, h3, h4 {color: #4DA8DA;}
    /* Pinta as barras de progresso do contrato com o Verde da Transforma */
    .stProgress > div > div > div > div {background-color: #1B7543;}
    </style>
    """, unsafe_allow_html=True)

# Topo com Logos Duplas e Título
col_logo1, col_titulo, col_logo2 = st.columns([1, 4, 1])
with col_logo1:
    try:
        st.image("Mothé Eng. Logo.png", width=90)
    except:
        st.write("⚡ Mothé")
with col_titulo:
    st.markdown("<h1 style='text-align: center;'>Painel de Engenharia | Transforma</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #A8B2C1;'><b>Mothé Engenharia</b> - Gestão de Contrato e Acompanhamento Técnico</p>", unsafe_allow_html=True)
with col_logo2:
    try:
        st.image("images.png", width=140) # Logo da Transforma
    except:
        st.write("♻️ Transforma")
st.divider()

# 2. Conectando com o Google Sheets
@st.cache_data(ttl=30)
def carregar_dados():
    SHEET_ID = "1LgXQeTJ4FK1h8VLGRWijU3oGaE_FNg5gBTuB6XhEiKI"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    df = pd.read_csv(url)
    
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

# 4. Gestão do Contrato (Visitas Físicas)
st.subheader("📊 Cumprimento do Contrato Anual (Visitas Físicas)")
col_meta1, col_meta2 = st.columns(2)

df_visitas = df.dropna(subset=['Data da Visita'])
visitas_macae = df_visitas[df_visitas['Base'].str.contains('Macaé', na=False)]['Data da Visita'].nunique()
visitas_inter = df_visitas[~df_visitas['Base'].str.contains('Macaé', na=False)]['Data da Visita'].nunique()

with col_meta1:
    st.metric("📍 Visitas Macaé (Meta: 104/ano)", f"{visitas_macae} realizadas")
    st.progress(min(visitas_macae / 104, 1.0))

with col_meta2:
    st.metric("📍 Visitas Gradim/Açu (Meta: 12/ano)", f"{visitas_inter} realizadas")
    st.progress(min(visitas_inter / 12, 1.0))
st.divider()

# 5. Indicadores Rápidos (KPIs)
col1, col2, col3, col4 = st.columns(4)
emergenciais = len(df_filtrado[df_filtrado["Prioridade"] == "Emergencial"])
concluidas = len(df_filtrado[df_filtrado["Status"] == "Resolvido"])
em_andamento = len(df_filtrado[df_filtrado["Status"] == "Em Andamento"])
pausadas = len(df_filtrado[df_filtrado["Status"].isin(["Pausado", "Aguardando Terceiros"])])

col1.metric("🚨 Atendimentos Emergenciais", emergenciais)
col2.metric("✅ Projetos Concluídos", concluidas)
col3.metric("⏳ Em Andamento", em_andamento)
col4.metric("⏸️ Pausados/Aguardando", pausadas)
st.divider()

# 6. INTELIGÊNCIA VISUAL: Gráficos Interativos
st.subheader("📈 Análise Gráfica")
col_g1, col_g2, col_g3 = st.columns(3)

# Paleta de cores semântica para os status
cor_status = {
    "Resolvido": "#1B7543", # Verde Transforma
    "Em Andamento": "#4DA8DA", # Azul Mothé
    "Não Iniciado": "#A8B2C1", # Cinza
    "Pausado": "#FF9F43", # Laranja
    "Aguardando Terceiros": "#EA5455", # Vermelho
    "Agendado": "#836AF9" # Roxo
}

with col_g1:
    st.markdown("**Distribuição por Status**")
    fig_status = px.pie(df_filtrado, names="Status", hole=0.4, color="Status", color_discrete_map=cor_status)
    fig_status.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), showlegend=False)
    fig_status.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_status, use_container_width=True)

with col_g2:
    st.markdown("**Status por Unidade (Gargalos)**")
    # Gráfico de barras agrupadas para comparar as bases
    fig_base = px.histogram(df_filtrado, x="Base", color="Status", barmode="group", color_discrete_map=cor_status)
    fig_base.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), xaxis_title="", yaxis_title="Quantidade", legend_title="")
    st.plotly_chart(fig_base, use_container_width=True)

with col_g3:
    st.markdown("**Volume por Categoria**")
    contagem_cat = df_filtrado["Categoria"].value_counts().reset_index()
    contagem_cat.columns = ["Categoria", "Quantidade"]
    fig_cat = px.bar(contagem_cat, x="Quantidade", y="Categoria", orientation='h', text_auto=True, color_discrete_sequence=["#4DA8DA"])
    fig_cat.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), xaxis_title="", yaxis_title="", yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_cat, use_container_width=True)

st.divider()

# 7. Preparando os Dados para as Tabelas
def calcular_progresso(fase):
    fase = str(fase).strip()
    if fase == "Levantamento em Campo": return 25
    if fase == "Engenharia de Escritório": return 50
    if fase in ["Em Aprovação (Cliente)", "Aguardando Terceiros"]: return 65
    if fase == "Em Execução": return 85
    if fase == "Concluído": return 100
    return 0

df_filtrado['Progresso'] = df_filtrado['Fase'].apply(calcular_progresso)
df_filtrado['Data de Início'] = df_filtrado['Data de Início'].dt.strftime('%d/%m/%Y').fillna('-')
df_filtrado['Data da Visita'] = df_filtrado['Data da Visita'].dt.strftime('%d/%m/%Y').fillna('Remoto/Escritório')
df_filtrado['Previsão de Conclusão'] = df_filtrado['Previsão de Conclusão'].dt.strftime('%d/%m/%Y').fillna('Contínuo / A definir')

df_futuro = df_filtrado[df_filtrado["Prioridade"] == "Planejamento (Futuro)"]
df_principal = df_filtrado[df_filtrado["Prioridade"] != "Planejamento (Futuro)"]

# 8. Tabela de Execução (Com Barra Animada)
st.subheader("📋 Histórico e Execução")
st.dataframe(
    df_principal[["Data de Início", "Data da Visita", "Base", "Categoria", "Descrição", "Fase", "Progresso", "Status", "Pendências/Observações"]],
    column_config={
        "Progresso": st.column_config.ProgressColumn("Avanço", help="Progresso baseado na fase", format="%d%%", min_value=0, max_value=100)
    },
    use_container_width=True, hide_index=True
)

# 9. Agenda Futura
st.subheader("📅 Planejamento e Agenda Futura")
if df_futuro.empty:
    st.info("Nenhuma atividade futura agendada no momento.")
else:
    st.dataframe(df_futuro[["Data de Início", "Base", "Categoria", "Descrição", "Status"]], use_container_width=True, hide_index=True)
