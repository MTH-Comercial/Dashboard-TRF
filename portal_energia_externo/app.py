"""Portal técnico público da Transforma — dados aprovados para apresentação externa.

Aplicação Streamlit independente do sistema de gestão interno. Não acessa
faturas originais, arquivos de medição brutos, bancos ou credenciais.
"""
from __future__ import annotations

from pathlib import Path
import json
import html
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Transforma | Painel técnico energético", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

ROOT = Path(__file__).resolve().parent
COLORS = {"blue": "#155f7a", "teal": "#13948b", "dark": "#12364d", "grey": "#647c88", "orange": "#c68c35"}

@st.cache_data(show_spinner=False)
def load_data() -> dict:
    with (ROOT / "dados.json").open(encoding="utf-8") as f:
        obj = json.load(f)
    required = {"elementos", "cenarios", "faturas_mt"}
    if not required.issubset(obj):
        raise ValueError("Conjunto de apresentação incompleto")
    return obj

DATA = load_data()
ITEMS = DATA["elementos"]
SCENARIOS = DATA["cenarios"]
BILLS = DATA["faturas_mt"]


def fmt(v, n=1):
    if v is None:
        return "—"
    try:
        return f"{float(v):,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "—"


def date_br(s: str) -> str:
    return pd.to_datetime(s).strftime("%d/%m/%Y") if s else "—"


def make_line(df, y_cols, labels=None, title=None, x="time", relative=False):
    fig = go.Figure()
    colors = [COLORS["teal"], COLORS["blue"], COLORS["orange"]]
    for idx, col in enumerate(y_cols):
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col], mode="lines", name=(labels or {}).get(col, col),
            line={"color": colors[idx % len(colors)], "width": 2.1},
            connectgaps=False,
            hovertemplate=f"%{{x}}<br>{(labels or {}).get(col, col)}: %{{y:,.1f}}<extra></extra>",
        ))
    fig.update_layout(
        title=title, height=385, margin=dict(l=8,r=12,t=35 if title else 12,b=8),
        plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.12, x=0),
        hovermode="x unified" if not relative else "closest",
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(gridcolor="#e5edf0", zeroline=False),
        font=dict(family="Arial", color="#29475a", size=12),
    )
    return fig


def card(title: str, content: str, description: str = ""):
    st.markdown(f'''<div class="metric-box"><div class="metric-label">{html.escape(title)}</div>
    <div class="metric-value">{html.escape(content)}</div><div class="metric-foot">{html.escape(description)}</div></div>''', unsafe_allow_html=True)


def section(title: str, subtitle=""):
    st.markdown(f"<h3 class='sect'>{html.escape(title)}</h3>", unsafe_allow_html=True)
    if subtitle:
        st.caption(subtitle)


st.markdown("""<style>
  .stApp {background: #f4f8fa; color: #19374a;}
  header[data-testid="stHeader"] {background: transparent;}
  .block-container {max-width: 1380px; padding-top: 1.8rem;}
  [data-testid="stSidebar"] {background: #10283a;}
  [data-testid="stSidebar"] * {color: #eef6f8 !important;}
  h1,h2,h3 {color:#12364d; letter-spacing:-.025em;}
  h1 {font-size: 2.2rem !important;}
  .sect {padding-top:.5rem; margin-bottom:.4rem;}
  .brand {display:flex;align-items:center;gap:.75rem;margin-bottom:.55rem}
  .brand-mark {background:#12364d;color:#f9fffe;width:50px;height:50px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:25px;}
  .brand-text {font-weight:800;font-size:20px;letter-spacing:.05em;color:#14364d}
  .brand-sub {font-size:11px;letter-spacing:.12em;color:#6e8895}
  .metric-box {border:1px solid #dce7ec;background:white;border-radius:13px;padding:18px 18px;min-height:128px;box-shadow: 0px 3px 18px #0a3b4908;}
  .metric-label {font-size:12px;color:#698391;font-weight:600;min-height:18px}
  .metric-value {font-size:27px;font-weight:760;color:#0b7373;margin-top:6px;letter-spacing:-.025em;}
  .metric-foot {font-size:11px;color:#698391; margin-top:5px;}
  .context {padding:16px 20px;background:#e5f2f2;border-left:4px solid #15958d;border-radius:6px;color:#315d65;margin:14px 0 22px;}
  .asset {padding:18px 20px; background:white; border:1px solid #dce7ec;border-radius:12px;min-height:215px;}
  .asset strong {display:block;font-size:15px;color:#15455b;padding:7px 0;}
  .asset .tag {font-size:11px;color:#117c79;font-weight:750;letter-spacing:.05em;}
  .asset p {color:#687f8b;font-size:12px;line-height:1.5;}
  .asset small {color:#547e8b;}
  .tiny-note {font-size:12px; color:#698391;}
  [data-testid="stMetric"] {background:white;border:1px solid #dce7ec;border-radius:12px;padding:14px;}
</style>""", unsafe_allow_html=True)

st.markdown('''<div class="brand"><div class="brand-mark">T</div><div><div class="brand-text">TRANSFORMA</div><div class="brand-sub">PAINEL TÉCNICO ENERGÉTICO · MACAÉ / RJ</div></div></div>''', unsafe_allow_html=True)

with st.sidebar:
    st.title("Painel técnico")
    page = st.radio("Navegação", [
        "Visão geral", "Pontos de medição", "Demanda de 15 minutos", "Simulação Bruno + Jaguar", "Entrada em média tensão", "Metodologia"
    ], label_visibility="collapsed")
    st.divider()
    st.caption("Consulta externa · somente leitura")
    st.caption("Campanhas históricas · última curadoria: " + date_br(DATA.get("atualizacao", "2026-11-18")))
    st.caption("Dados consolidados para apoio a projetos. Não há autenticação.")

if page == "Visão geral":
    st.title("Infraestrutura e comportamento elétrico")
    st.write("Consolidação das medições em transformadores de distribuição interna e nos trituradores da área de blend, para apoio à elaboração de estudos e projetos.")
    st.markdown('<div class="context"><b>Escopo:</b> TR1–TR3 são alimentados pela rede de média tensão, com saída de 220 V entre fases. Bruno e Jaguar utilizam geradores a diesel em 380 V. As campanhas dos trituradores foram realizadas em anos diferentes; cenários combinados são apenas simulações.</div>', unsafe_allow_html=True)
    section("Distribuição funcional das cargas", "Identificação dos principais circuitos associados a cada ponto de medição")
    c = st.columns(3)
    for i, e in enumerate(ITEMS):
        with c[i % 3]:
            st.markdown(f'''<div class="asset"><span class="tag">{html.escape(e['tipo'])} · {html.escape(e['tensao'])}</span>
            <strong>{html.escape(e['nome'])}</strong><p>{html.escape(e['descricao'])}</p>
            <small>Campanha: {date_br(e['inicio'])} a {date_br(e['fim'])}</small></div>''', unsafe_allow_html=True)
            st.write("")
    section("Síntese das campanhas")
    cols = st.columns(4)
    with cols[0]: card("Pontos instrumentados", str(len(ITEMS)), "3 transformadores + 2 trituradores")
    with cols[1]: card("Campanhas distintas", str(len(ITEMS)), "Não simultâneas")
    with cols[2]: card("Registros históricos", fmt(sum(x['registros'] for x in ITEMS), 0), "Soma de todos os pontos")
    with cols[3]: card("Faturas com indicadores MT", str(len(BILLS)), "Dados técnicos, sem valores financeiros")
    st.info("A energia registrada em pontos alimentados por geradores não integra, nesses períodos, a energia faturada pela Enel no ponto de entrega.")

elif page == "Pontos de medição":
    st.title("Pontos de medição")
    code_to_item = {x['codigo']:x for x in ITEMS}
    code = st.selectbox("Selecionar transformador ou triturador", list(code_to_item), format_func=lambda k: code_to_item[k]['nome'])
    e = code_to_item[code]
    st.write(f"**{e['tipo']} · {e['tensao']}** — {e['descricao']}")
    st.caption(f"Campanha: {date_br(e['inicio'])} a {date_br(e['fim'])}")
    cols = st.columns(4)
    with cols[0]:card("P15 máxima móvel", f"{fmt(e['p15_max_kw'])} kW", "Média móvel de 15 minutos")
    with cols[1]:card("S15 máxima", f"{fmt(e['s15_max_kva'])} kVA", "Potência aparente média")
    with cols[2]:card("Energia registrada", f"{fmt(e['energia_kwh'],0)} kWh", "Somente intervalos válidos")
    with cols[3]:card("Registros válidos", f"{fmt(100 * e['validos']/e['registros'])}%", f"{e['validos']} de {e['registros']}")
    section("Curva histórica", "A série representada é uma amostragem para apresentação; os indicadores de máximos usam os registros completos válidos")
    quantity = st.radio("Grandeza", ["Potência ativa · kW", "Potência aparente · kVA"], horizontal=True)
    df = pd.DataFrame(e.get("curva15", []))
    if df.empty:
        st.warning("Não foram disponibilizadas janelas completas para este ponto.")
    else:
        df["time"] = pd.to_datetime(df["data"])
        k = "kw" if "ativa" in quantity else "kva"
        st.plotly_chart(make_line(df, [k], {"kw":"Potência ativa (kW)","kva":"Potência aparente (kVA)"}), use_container_width=True)
    section("Energia por dia")
    d = pd.DataFrame(e.get("dias", []))
    if not d.empty:
        d["time"] = pd.to_datetime(d["data"])
        st.bar_chart(d.set_index("time")["kwh"], x_label="Dia da campanha", y_label="Energia registrada (kWh)", color=COLORS["teal"])
        st.caption("Dias sem registro de energia não podem ser considerados dias de consumo nulo.")
    section("Métricas adicionais")
    more = st.columns(4)
    with more[0]: st.metric("P5 máxima", f"{fmt(e['p5_max_kw'])} kW")
    with more[1]: st.metric("S5 máxima", f"{fmt(e['s5_max_kva'])} kVA")
    with more[2]: st.metric("Pico aparente intra-5 min", f"{fmt(e['s_intra_kva'])} kVA")
    with more[3]: st.metric("Percentil 95 P15", f"{fmt(e['p15_p95_kw'])} kW")
    if e['codigo'] in ('BRUNO','JAGUAR'):
        c1,c2,c3=st.columns(3)
        with c1: st.metric("Energia média/dia ativo", f"{fmt(e['energia_media_dia_ativo_kwh'])} kWh")
        with c2: st.metric("Energia média/episódio", f"{fmt(e['energia_media_episodio_kwh'])} kWh")
        with c3: st.metric("Episódios identificados", str(e['episodios']))

elif page == "Demanda de 15 minutos":
    st.title("Comparação das campanhas")
    st.caption("As cinco campanhas ocorreram em períodos distintos e não formam uma curva simultânea de toda a planta.")
    rows=[]
    for e in ITEMS:
        rows.append({
            "Ponto":e["nome"], "Período":f"{date_br(e['inicio'])}–{date_br(e['fim'])}",
            "Energia (kWh)":e['energia_kwh'], "P máx. 5 min (kW)":e['p5_max_kw'],
            "P máx. 15 min (kW)":e['p15_max_kw'], "S máx. 5 min (kVA)":e['s5_max_kva'],
            "S máxima intra-5 min (kVA)":e['s_intra_kva'],
            "Cobertura (%)":100*e['validos']/e['registros']
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, column_config={
        "Energia (kWh)":st.column_config.NumberColumn(format="%.1f"),
        "P máx. 5 min (kW)":st.column_config.NumberColumn(format="%.1f"),
        "P máx. 15 min (kW)":st.column_config.NumberColumn(format="%.1f"),
        "S máx. 5 min (kVA)":st.column_config.NumberColumn(format="%.1f"),
        "S máxima intra-5 min (kVA)":st.column_config.NumberColumn(format="%.1f"),
        "Cobertura (%)":st.column_config.NumberColumn(format="%.1f"),
    })
    chartdf=pd.DataFrame([{"Ponto":x['codigo'],"P5":x['p5_max_kw'],"P15":x['p15_max_kw']} for x in ITEMS]).set_index("Ponto")
    st.bar_chart(chartdf, x_label="Ponto de medição",y_label="Potência ativa (kW)")
    st.info("A demanda de 15 minutos é calculada a partir dos registros de energia/potência válidos. Os picos em kVA dentro de cinco minutos NÃO são demanda contratual em kW.")

elif page == "Simulação Bruno + Jaguar":
    st.title("Bruno + Jaguar — sobreposição hipotética")
    st.markdown('<div class="context"><b>Atenção:</b> Bruno (2024) e Jaguar (2026) foram instrumentados separadamente. O gráfico é uma simulação de alinhamento histórico; não representa medição conjunta nem garante a máxima demanda real.</div>', unsafe_allow_html=True)
    opt=st.selectbox("Hipótese de alinhamento", ["dia_hora", "episodios"], format_func=lambda k: "Dias ativos equivalentes e mesmo horário" if k == "dia_hora" else "Início de episódios de trituração equivalentes")
    s=SCENARIOS[opt]
    cols=st.columns(4)
    with cols[0]:card("Demanda P15 sintética máxima",f"{fmt(s['p15_max_kw'])} kW","Média de 15 minutos")
    with cols[1]:card("S15 por soma de magnitudes",f"{fmt(s['s15_soma_aritmetica_max_kva'])} kVA","Envoltória, não soma fasorial")
    with cols[2]:card("P5 sintética máxima",f"{fmt(s['p5_max_kw'])} kW","Média de 5 minutos")
    with cols[3]:card("Janelas pareadas válidas",fmt(s['janelas_pareadas_15min'],0),"Ambos com registros no alinhamento")
    section("Perfil de demanda simulado")
    df=pd.DataFrame(s['janelas_15min_amostra']).reset_index().rename(columns={"index":"posição"})
    if not df.empty:
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=df["posição"],y=df["p15_kw"],mode="lines",name="P15 sintética · kW",line={"color":COLORS['teal'],"width":2},customdata=df['marcador'],hovertemplate="Ponto %{customdata}<br>P15: %{y:.1f} kW<extra></extra>"))
        fig.update_layout(height=380,plot_bgcolor="white",margin=dict(l=12,r=12,t=20,b=20),xaxis_title="Sequência dos pontos de amostragem pareados",yaxis_title="Potência ativa (kW)",yaxis=dict(gridcolor="#e5edf0"))
        st.plotly_chart(fig,use_container_width=True)
    st.caption(s.get('aviso',''))
    section("Grandezas adicionais do cenário")
    x1,x2,x3=st.columns(3)
    with x1:st.metric("P95 de P15",f"{fmt(s['p15_p95_kw'])} kW")
    with x2:st.metric("S máxima intra-5 min (alinhada)",f"{fmt(s['s_intra_soma_aritmetica_max_kva'])} kVA")
    with x3:st.metric("Soma dos picos isolados intra-5 min",f"{fmt(s['s_intra_maximos_individuais_soma_kva'])} kVA")
    st.warning("Os valores são específicos da hipótese escolhida, com defasagem de 0 minuto. Não se deve usar diretamente a curva como medição fiscal da Enel nem para aprovar a potência de transformador. Confirme simultaneidade, partidas, transitórios e outras cargas da futura subestação.")

elif page == "Entrada em média tensão":
    st.title("Entrada em média tensão — indicadores mensais")
    st.caption("Dados técnicos transcritos das faturas Enel de janeiro a agosto/2026. Não são medições individuais dos transformadores ou dos geradores diesel.")
    f=pd.DataFrame(BILLS)
    f['consumo_kwh']=f['energia_ponta_kwh']+f['energia_fora_kwh']
    f['mes_label']=pd.to_datetime(f['mes']).dt.strftime('%m/%Y')
    cols=st.columns(4)
    with cols[0]:card("Maior demanda fora ponta",f"{fmt(f['demanda_fora_kw'].max())} kW","Máxima dentre meses disponíveis")
    with cols[1]:card("Demanda contratada",f"{fmt(f['contratada_kw'].iloc[-1])} kW","Última fatura disponível")
    with cols[2]:card("Consumo histórico consolidado",f"{fmt(f['consumo_kwh'].sum(),0)} kWh","Soma dos oito períodos")
    with cols[3]:card("Períodos analisados",str(len(f)),"Jan–ago/2026")
    section("Demanda fora de ponta por mês")
    fig=go.Figure()
    fig.add_trace(go.Bar(x=f['mes_label'],y=f['demanda_fora_kw'],name="Registrada (kW)",marker_color=COLORS['blue']))
    fig.add_trace(go.Scatter(x=f['mes_label'],y=f['contratada_kw'],mode="lines+markers",name="Contratada (kW)",line=dict(color=COLORS['orange'],dash='dash',width=2)))
    fig.update_layout(height=385,plot_bgcolor='white',yaxis=dict(gridcolor="#e5edf0",title="Demanda (kW)"),xaxis_title="Mês",margin=dict(l=8,r=8,t=12,b=10),legend=dict(orientation='h',y=1.13))
    st.plotly_chart(fig,use_container_width=True)
    section("Energia mensal na entrada MT")
    st.bar_chart(f.set_index('mes_label')['consumo_kwh'],x_label="Mês",y_label="Energia (kWh)",color=COLORS['teal'])
    view=f[['mes_label','demanda_ponta_kw','demanda_fora_kw','contratada_kw','consumo_kwh']].rename(columns={'mes_label':'Mês','demanda_ponta_kw':'Demanda ponta (kW)','demanda_fora_kw':'Demanda fora ponta (kW)','contratada_kw':'Contratada (kW)','consumo_kwh':'Energia total (kWh)'})
    st.dataframe(view,hide_index=True,use_container_width=True)
    st.info("Não são divulgados neste portal valores financeiros, tarifas, notas fiscais, créditos ou faturas digitalizadas.")

else:
    st.title("Metodologia e limitações")
    st.markdown('''
    **Origem.** Informações consolidadas a partir de campanhas com analisador de energia em TR1, TR2, TR3, Bruno e Jaguar, além de indicadores técnicos de faturas da concessionária.

    **Janelas de 15 minutos.** Para reconstrução, utilizam-se três intervalos consecutivos válidos de cinco minutos. Janelas com lacunas não são completadas com zero. Os maiores valores são calculados sobre a série íntegra processada, embora alguns gráficos exibam séries amostradas.

    **Demanda tarifária.** A grandeza faturável é demanda ativa, em kW, medida no ponto de entrega em média tensão; não corresponde ao maior pico aparente transitório em kVA.

    **Trituradores.** Os registros do Bruno são de 2024, os do Jaguar são de 2026. As simulações alinham artificialmente períodos de carga separados, sem comprovar simultaneidade real. O somatório de magnitudes em kVA é uma aproximação conservadora, não uma soma vetorial de potências complexas.

    **Consumo.** A energia representa apenas intervalos válidos da medição. Dias de parada, desligamento de gerador ou falta de registros exigem confirmação operacional.

    **Dimensionamento.** Este conjunto não substitui estudos de cargas, partidas, curto-circuito, proteção, coordenação, transformadores, qualidade de energia nem medições sincronizadas. A engenharia de projeto deve definir fatores de simultaneidade e de ampliação previstos.

    **Privacidade.** Este é o painel de divulgação técnica, sem senha. Dados nele exibidos ficam acessíveis a qualquer pessoa que tenha o link. Não possui função de editar, importar ou acessar bases internas.
    ''')

st.divider()
st.caption("TRANSFORMA · Painel técnico energético · Dados consolidados para consulta externa · Revisão de apresentação 4.0")