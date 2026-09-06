import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração da Página (Tema Escuro e Layout Largo)
st.set_page_config(page_title="Painel Transforma | Mothé Engenharia", layout="wide")

# Forçando cores corporativas via CSS (Azul Escuro/Cinza)
st.markdown("""
    <style>
    .main {background-color: #0E1117;}
    h1, h2, h3 {color: #4DA8DA;}
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Painel de Controle de Engenharia | Transforma")
st.markdown("**Mothé Engenharia** - Acompanhamento Mensal de Atividades e Projetos")
st.divider()

# 2. Conectando com o Google Sheets
@st.cache_data(ttl=60)
def carregar_dados():
    # ID exato da sua planilha
    SHEET_ID = "1LgXQeTJ4FK1h8VLGRWijU3oGaE_FNg5gBTuB6XhEiKI"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    df = pd.read_csv(url)
    return df

df = carregar_dados()

# 3. Filtros na Barra Lateral (Sidebar)
st.sidebar.header("⚙️ Filtros do Painel")
base_selecionada = st.sidebar.multiselect("Selecione a Base:", options=df["Base"].unique(), default=df["Base"].unique())
status_selecionado = st.sidebar.multiselect("Selecione o Status:", options=df["Status"].unique(), default=df["Status"].unique())

# Aplicando os filtros
df_filtrado = df.query("Base in @base_selecionada and Status in @status_selecionado")

# 4. Cartões de Indicadores (KPIs)
col1, col2, col3, col4 = st.columns(4)
total_atividades = len(df_filtrado)
concluidas = len(df_filtrado[df_filtrado["Status"] == "Resolvido"])
em_andamento = len(df_filtrado[df_filtrado["Status"] == "Em Andamento"])
pendentes = len(df_filtrado[df_filtrado["Status"].isin(["Não Iniciado", "Aguardando Terceiro/Compras"])])

col1.metric("Total de Atividades", total_atividades)
col2.metric("Atividades Concluídas", concluidas)
col3.metric("Em Andamento", em_andamento)
col4.metric("Pendentes / Aguardando", pendentes)

st.divider()

# 5. Gráficos Interativos (Plotly)
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    st.subheader("Distribuição por Status")
    fig_status = px.pie(df_filtrado, names="Status", hole=0.4, color_discrete_sequence=px.colors.sequential.Blues_r)
    fig_status.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
    st.plotly_chart(fig_status, use_container_width=True)

with col_graf2:
    st.subheader("Atividades por Categoria")
    contagem_categoria = df_filtrado["Categoria"].value_counts().reset_index()
    contagem_categoria.columns = ["Categoria", "Quantidade"]
    fig_categoria = px.bar(contagem_categoria, x="Categoria", y="Quantidade", text_auto=True, color_discrete_sequence=["#4DA8DA"])
    fig_categoria.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
    st.plotly_chart(fig_categoria, use_container_width=True)

st.divider()

# 6. Tabela Detalhada
st.subheader("📋 Lista Detalhada de Atividades")
st.dataframe(df_filtrado[["ID da Tarefa", "Data de Registro", "Base", "Categoria", "Descrição", "Fase", "Progresso (%)", "Status"]], use_container_width=True)