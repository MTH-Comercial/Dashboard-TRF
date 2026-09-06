import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração Inicial
st.set_page_config(page_title="Painel Transforma | Mothé Engenharia", layout="wide", page_icon="⚡", initial_sidebar_state="collapsed")

# ==========================================
# 🔒 SISTEMA DE LOGIN COM PERSISTÊNCIA (F5 Friend)
# ==========================================
params = st.query_params

if "autenticado" not in st.session_state:
    # Se o link já tiver o passe livre, mantém logado
    if params.get("auth") == "true":
        st.session_state["autenticado"] = True
    else:
        st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #4DA8DA;'>⚡ Mothé Engenharia</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: white;'>Acesso Restrito ao Cliente</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #A8B2C1;'>Por favor, insira a senha de acesso da unidade Transforma.</p>", unsafe_allow_html=True)
    
    col_espaco1, col_login, col_espaco2 = st.columns([1, 1, 1])
    with col_login:
        senha_digitada = st.text_input("Senha de Acesso:", type="password")
        if st.button("Entrar no Painel", use_container_width=True):
            # VVV --- SUA SENHA --- VVV
            if senha_digitada == "Transforma2026": 
                st.session_state["autenticado"] = True
                # Carimba o navegador para o F5 não pedir senha de novo
                st.query_params["auth"] = "true"
                st.rerun()
            else:
                st.error("Senha incorreta. Acesso negado.")
    
    st.stop() 
# ==========================================

# A partir daqui, o site está liberado!

st.markdown("""
    <style>
    .main {background-color: #0E1117;}
    h1, h2, h3, h4 {color: #4DA8DA;}
    .stProgress > div > div > div > div {background-color: #1B7543;}
    [data-testid="collapsedControl"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

# Topo Premium
st.markdown("""
    <div style="background: linear-gradient(90deg, rgba(14,17,23,1) 0%, rgba(30,38,56,1) 50%, rgba(14,17,23,1) 100%);
                padding: 40px 20px;
                border-radius: 15px;
                border-bottom: 3px solid #4DA8DA;
                text-align: center;
                margin-bottom: 30px;
                box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.5);">
        <h1 style="color: white; margin-bottom: 0px; font-size: 3.2rem;">Painel de Engenharia <span style="color: #4DA8DA;">|</span> <span style="color: #1B7543;">Transforma</span></h1>
        <p style="color: #A8B2C1; font-size: 1.2rem; margin-top: 10px;"><b>Mothé Engenharia</b> - Gestão de Contrato e Acompanhamento Técnico</p>
    </div>
""", unsafe_allow_html=True)

# 2. Conectando com o Google Sheets
@st.cache_data(ttl=30)
def carregar_dados():
    SHEET_ID = "1LgXQeTJ4FK1h8VLGRWijU3oGaE_FNg5gBTuB6XhEiKI"
    url_principal = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1562629984"
    df = pd.read_csv(url_principal)
    
    GID_DIARIO = "997870532" 
    url_diario = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_DIARIO}"
    df_diario = pd.read_csv(url_diario)
    
    df['Data de Início'] = pd.to_datetime(df['Data de Início'], format='%d/%m/%Y', errors='coerce')
    df['Data da Visita'] = pd.to_datetime(df['Data da Visita'], format='%d/%m/%Y', errors='coerce')
    df['Previsão de Conclusão'] = pd.to_datetime(df['Previsão de Conclusão'], format='%d/%m/%Y', errors='coerce')
    if 'Subárea' not in df.columns: df['Subárea'] = '-'
    df_diario['Data da Atualização'] = pd.to_datetime(df_diario['Data da Atualização'], format='%d/%m/%Y', errors='coerce')
    
    return df, df_diario

df, df_diario = carregar_dados()

# 3. FILTROS INTEGRADOS
st.markdown("### 🎛️ Filtros de Análise")
col_filtro1, col_filtro2 = st.columns(2)
with col_filtro1:
    base_selecionada = st.multiselect("Selecione a Base/Unidade:", options=df["Base"].dropna().unique(), default=df["Base"].dropna().unique())
with col_filtro2:
    status_selecionado = st.multiselect("Selecione o Status:", options=df["Status"].dropna().unique(), default=df["Status"].dropna().unique())

df_filtrado = df.query("Base in @base_selecionada and Status in @status_selecionado").copy()
st.divider()

# 4. Gestão do Contrato (Visitas Físicas)
st.subheader("📊 Cumprimento do Contrato Anual (Visitas Físicas)")
col_meta1, col_meta2 = st.columns(2)
hoje = pd.Timestamp.now().normalize()
df_visitas_realizadas = df.dropna(subset=['Data da Visita'])
df_visitas_realizadas = df_visitas_realizadas[df_visitas_realizadas['Data da Visita'] <= hoje]

visitas_macae = df_visitas_realizadas[df_visitas_realizadas['Base'].str.contains('Macaé', na=False)]['Data da Visita'].nunique()
visitas_inter = df_visitas_realizadas[~df_visitas_realizadas['Base'].str.contains('Macaé', na=False)]['Data da Visita'].nunique()

with col_meta1:
    st.metric("📍 Visitas Macaé (Meta: 104/ano)", f"{visitas_macae} realizadas")
    st.progress(min(visitas_macae / 104, 1.0))
with col_meta2:
    st.metric("📍 Visitas Gradim/Açu (Meta: 12/ano)", f"{visitas_inter} realizadas")
    st.progress(min(visitas_inter / 12, 1.0))
st.divider()

# 5. KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("🚨 Atendimentos Emergenciais", len(df_filtrado[df_filtrado["Prioridade"] == "Emergencial"]))
col2.metric("✅ Projetos Concluídos", len(df_filtrado[df_filtrado["Status"] == "Resolvido"]))
col3.metric("⏳ Em Andamento", len(df_filtrado[df_filtrado["Status"] == "Em Andamento"]))
col4.metric("⏸️ Pausados/Aguardando", len(df_filtrado[df_filtrado["Status"].isin(["Pausado", "Aguardando Terceiros"])]))

# 6. Gráficos
st.subheader("📈 Análise de Área e Produção")
cor_status = {"Resolvido": "#1B7543", "Em Andamento": "#4DA8DA", "Não Iniciado": "#A8B2C1", "Pausado": "#FF9F43", "Aguardando Terceiros": "#EA5455", "Agendado": "#836AF9"}
cor_bases = {"Macaé/RJ": "#1B7543", "Gradim - São Gonçalo/RJ": "#4DA8DA", "Porto do Açu - São João da Barra/RJ": "#FF9F43"}

linha1_col1, linha1_col2 = st.columns(2)
with linha1_col1:
    fig_status = px.pie(df_filtrado, names="Status", hole=0.4, color="Status", color_discrete_map=cor_status, title="Distribuição por Status Geral")
    fig_status.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), showlegend=False)
    fig_status.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_status, use_container_width=True)

with linha1_col2:
    contagem_cat = df_filtrado["Categoria"].value_counts().reset_index()
    contagem_cat.columns = ["Categoria", "Quantidade"]
    fig_cat = px.bar(contagem_cat, x="Quantidade", y="Categoria", orientation='h', text_auto=True, color_discrete_sequence=["#4DA8DA"], title="Volume por Categoria de Engenharia")
    fig_cat.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), xaxis_title="", yaxis_title="", yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_cat, use_container_width=True)

linha2_col1, linha2_col2 = st.columns(2)
with linha2_col1:
    contagem_sub = df_filtrado.groupby(["Subárea", "Base"]).size().reset_index(name="Quantidade")
    fig_sub = px.bar(contagem_sub, x="Subárea", y="Quantidade", color="Base", text_auto=True, color_discrete_map=cor_bases, title="Volume de Atividades por Subárea")
    fig_sub.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), xaxis_title="", yaxis_title="Tarefas", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""))
    st.plotly_chart(fig_sub, use_container_width=True)

with linha2_col2:
    fig_base = px.histogram(df_filtrado, x="Base", color="Status", barmode="group", color_discrete_map=cor_status, title="Gargalos por Base Principal")
    fig_base.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), xaxis_title="", yaxis_title="Quantidade", legend_title="")
    st.plotly_chart(fig_base, use_container_width=True)

st.divider()

# 7. Tratamento de Dados 
def calcular_progresso(fase):
    fase = str(fase).strip()
    if fase == "Levantamento em Campo": return 25
    if fase == "Engenharia de Escritório": return 50
    if fase in ["Em Aprovação (Cliente)", "Aguardando Terceiros"]: return 65
    if fase == "Em Execução": return 85
    if fase == "Concluído": return 100
    return 0

mask_futuro = (df_filtrado['Data de Início'] > hoje) | (df_filtrado['Prioridade'] == "Planejamento (Futuro)")
df_futuro = df_filtrado[mask_futuro].copy()
df_principal = df_filtrado[~mask_futuro].copy()

def formatar_tabelas(df_temp):
    df_temp['Progresso'] = df_temp['Fase'].apply(calcular_progresso)
    df_temp['Data de Início'] = df_temp['Data de Início'].dt.strftime('%d/%m/%Y').fillna('-')
    df_temp['Data da Visita'] = df_temp['Data da Visita'].dt.strftime('%d/%m/%Y').fillna('Remoto/Escritório')
    df_temp['Previsão de Conclusão'] = df_temp['Previsão de Conclusão'].dt.strftime('%d/%m/%Y').fillna('Contínuo / A definir')
    df_temp['Pendências/Observações'] = df_temp['Pendências/Observações'].fillna('Nenhuma observação principal.')
    return df_temp

df_futuro = formatar_tabelas(df_futuro)
df_principal = formatar_tabelas(df_principal)

# 8. HISTÓRICO EXPANSÍVEL
st.subheader("📋 Histórico e Execução")
st.markdown("Clique em uma tarefa abaixo para ver os detalhes e a **Linha do Tempo (Diário de Bordo)**.")

if df_principal.empty:
    st.info("Nenhuma atividade encontrada com os filtros atuais.")
else:
    for index, row in df_principal.iterrows():
        id_tarefa = row["ID da Tarefa"]
        icone_status = "✅" if row["Status"] == "Resolvido" else "⏳" if row["Status"] == "Em Andamento" else "⏸️"
        titulo_caixa = f"{icone_status} [{row['Status']}] {row['Base']} ({row['Subárea']}) - {row['Categoria']}"
        
        with st.expander(titulo_caixa):
            col_detalhe1, col_detalhe2 = st.columns([1, 2])
            with col_detalhe1:
                st.markdown(f"**ID:** `{id_tarefa}`")
                st.markdown(f"**Início:** {row['Data de Início']}")
                st.markdown(f"**Visita:** {row['Data da Visita']}")
                st.markdown(f"**Fase Atual:** {row['Fase']}")
                st.progress(row['Progresso'] / 100)
            with col_detalhe2:
                st.markdown(f"**📝 Descrição Inicial / Escopo:**")
                st.info(row['Descrição'])
            st.divider()
            
            st.markdown("### 📜 Linha do Tempo (Atualizações)")
            historico_tarefa = df_diario[df_diario["ID da Tarefa"] == id_tarefa].copy()
            if historico_tarefa.empty:
                st.warning("Nenhuma atualização registrada no Diário de Bordo para esta tarefa.")
            else:
                historico_tarefa = historico_tarefa.sort_values(by="Data da Atualização", ascending=False)
                for _, hist_row in historico_tarefa.iterrows():
                    data_formatada = hist_row['Data da Atualização'].strftime('%d/%m/%Y')
                    st.markdown(f"**📅 {data_formatada} | {hist_row['Fase Atualizada']}** *(Status: {hist_row['Status Atualizado']})*")
                    st.write(f"↳ {hist_row['Descrição do que aconteceu']}")
                    st.write("") 

# 9. Agenda Futura
st.divider()
st.subheader("📅 Planejamento e Agenda Futura")
if df_futuro.empty:
    st.info("Nenhuma atividade futura agendada no momento.")
else:
    st.dataframe(df_futuro[["Data de Início", "Base", "Subárea", "Categoria", "Descrição", "Status"]], use_container_width=True, hide_index=True)
