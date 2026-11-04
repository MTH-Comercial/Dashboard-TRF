"""Dashboard Transforma v2 | Mothé Engenharia — painel do cliente + gestão admin."""
from __future__ import annotations
from datetime import date
from html import escape
from pathlib import Path
import io
import hashlib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analytics import (
    BASES, CATEGORIES, PHASES, PRIORITIES, STATUSES, CLOSED,
    ALL_TASK_COLUMNS, TASK_EXTRA_COLUMNS, KIND_OPTIONS, ACT_KIND_OPTIONS, WAITING_STATUSES, DEADLINE_KINDS,
    display_status, effective_closed, ALL_VISIT_COLUMNS, VISIT_PURPOSES,
    delivery_frame, delivery_overview, is_radar, activity_only_frame,
    TASK_COLUMNS, DIARY_COLUMNS, VISIT_COLUMNS, ALL_VISIT_COLUMNS,
    contract_metrics, contract_window, diary_frame, format_date,
    location_group, pct, quality_issues, task_frame, task_metrics,
    visit_frame, visits_from_register, visits_from_tasks, parse_date, today_brazil, sort_tasks_for_table,
)
from security import verify_password
from preview import parse_uploaded_workbook
from storage import (
    add_diary_and_update, add_visit, create_task, demo_mode, google_ready,
    initialize_visits_from_tasks, load_all, secret, update_task, update_visit,
    clear_data_cache, demo_replace_dataset,
)

st.set_page_config(
    page_title='Transforma | Painel de Engenharia', page_icon='⚡',
    layout='wide', initial_sidebar_state='expanded',
)

# UI theme — input controls and charts remain native, accessible Streamlit widgets.
st.markdown('''<style>
/* Evita sobreposição do cabeçalho pela barra superior Streamlit. */
[data-testid="stAppViewContainer"] .block-container {
  max-width: 1510px; padding-top: 5rem !important; padding-bottom: 3rem;
}
@media(max-width:768px){[data-testid="stAppViewContainer"] .block-container { padding-top: 4.5rem !important; }}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] .block-container { padding-top: 1.5rem !important; }

[data-testid="stSidebar"] { background: #0C1625; border-right: 1px solid #1D2C42; }
[data-testid="stSidebar"] .stRadio label { padding-top: .15rem; padding-bottom: .15rem; }
h1, h2, h3 { letter-spacing: -.025em; }
h3 { color: #E5EDF7; }
div[data-testid="stMetric"] {
  background: linear-gradient(140deg,#17253A 0%,#101B2B 100%);
  border: 1px solid #2A3E57; border-radius: 16px;
  padding: 1.05rem 1.15rem;
  min-height: 130px;
}
[data-testid="stMetricLabel"] { color: #A4B8D1 !important; }
[data-testid="stMetricValue"] { color: #F0F5FE !important; letter-spacing: -.05em; }
div[data-testid="stVerticalBlockBorderWrapper"] > div {
  border-color: #25364B !important; border-radius: 16px !important;
}
.stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"] {
  border-radius: 11px; background: #2096D2; border-color: #2096D2;
  font-weight: 700; color: #fff;
}
.stButton button, .stFormSubmitButton button { border-radius: 11px; }
.header-panel {
  padding: 23px 28px; border: 1px solid #284568; border-radius: 18px;
  background: radial-gradient(circle at 90% -10%,rgba(33,154,230,.23),transparent 35%),
              linear-gradient(115deg,#172943 0%,#0B1728 100%);
  margin: .65rem 0 22px 0;
}
.eyebrow { color: #74BDE9; text-transform: uppercase; letter-spacing: .13em;
  font-weight: 800; font-size: .72rem; margin-bottom: 6px; }
.hero-title { font-size: clamp(1.6rem,3vw,2.2rem); font-weight: 800; color: #F4F8FE;
  letter-spacing: -.035em; margin: 0 0 4px 0; }
.hero-subtitle { color: #B0C3DA; font-size: .93rem; margin: 0; }
.section-note { font-size: .81rem; color: #92A9C5; margin-bottom: .65rem; }
.soft-badge { border-radius: 20px; padding: 3px 10px; background: #183A54;
  color: #88D1FF; font-size: .78rem; }
.compact-kpi {background:linear-gradient(140deg,#16273E,#101B2B);border:1px solid #2D405B;
  border-top:3px solid var(--accent);border-radius:15px;padding:16px 17px;
  min-height:118px;display:flex;flex-direction:column;justify-content:space-between;margin-bottom:9px;}
.compact-kpi-label {font-size:.84rem;color:#AEC3DD;font-weight:650;line-height:1.24}
.compact-kpi-value {font-size:2rem;line-height:1.13;font-weight:760;color:#F0F6FF;letter-spacing:-.05em;margin:4px 0}
.compact-kpi-detail {font-size:.72rem;color:#91A9C4;line-height:1.32;min-height:1.0rem}
.mini-progress {height:8px;border-radius:8px;background:#24344B;overflow:hidden;margin:.45rem 0;}
.mini-progress span {display:block;height:100%;border-radius:8px;background:#34A8EB;}
.contract-strip {background:#122239;border:1px solid #29405E;border-radius:16px;padding:14px 17px;margin-bottom:8px;}
.contract-strip-title {font-size:.83rem;color:#BDCEE2;font-weight:650}
.contract-strip-number {font-size:1.45rem;font-weight:780;color:#F0F6FF}
.contract-strip-foot {font-size:.72rem;color:#9FB6D0}
</style>''', unsafe_allow_html=True)

COLOR_STATUS = {
    'Resolvido': '#35C99A', 'Em Andamento': '#35A8E9',
    'Pausado': '#F7B955', 'Aguardando Terceiros': '#EA7386',
    'Aguardando Terceiro/Compras': '#EA7386', 'Aguardando': '#F7B955',
    'Não Iniciado': '#8D9EB5', 'Agendado': '#B095EC',
    'Realizado':'#35C99A','Realizada':'#35C99A','Concluído':'#35C99A',
    'Aguardando Cliente':'#F3B653', 'Aguardando Aprovação':'#F3B653',
    'Aguardando Materiais':'#F3B653', 'Em Validação':'#A5B8FB', 'Bloqueado':'#EA7386',
}
PLOT_FONT = dict(family='Inter, Arial, sans-serif', color='#C8D6E8', size=12)


def kpi_card(label, value, detail='', accent='#35A8E9'):
    """Um KPI realmente compacto, com a legenda no mesmo cartão."""
    st.markdown(
        f'<div class="compact-kpi" style="--accent:{accent}">'
        f'<div class="compact-kpi-label">{escape(str(label))}</div>'
        f'<div class="compact-kpi-value">{escape(str(value))}</div>'
        f'<div class="compact-kpi-detail">{escape(str(detail))}</div>'
        '</div>', unsafe_allow_html=True)


def compact_table(data, *, key='', height=237):
    """Todas as atividades no quadro, com rolagem limitada a cinco linhas visíveis."""
    if data.empty:
        st.info('Nenhum registro nesta seleção.')
        return
    order = data.copy()
    date_col = 'Data de Início_dt'
    if date_col in order.columns:
        order = order.sort_values(date_col, ascending=False, na_position='last')
    order['Situação'] = order.apply(lambda r: display_status(r.get('Tipo de Registro',''),r.get('Status','')),axis=1)
    use = ['ID da Tarefa','Descrição','Base','Situação']
    if 'Motivo de Espera' in order.columns and key == 'prioridades':
        use += ['Motivo de Espera']
    st.dataframe(order[use].rename(columns={'ID da Tarefa':'ID','Motivo de Espera':'Dependência'}),
                 hide_index=True, use_container_width=True, height=height,
                 column_config={'Descrição':st.column_config.TextColumn(width='large'),
                                'Dependência':st.column_config.TextColumn(width='medium')})


def style_figure(fig, height=350):
    fig.update_layout(
        template='plotly_dark', height=height, margin=dict(l=12,r=12,t=24,b=16),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=PLOT_FONT, legend_title_text='',
        hoverlabel=dict(bgcolor='#15263B', font_color='#E5F0FF'),
    )
    fig.update_xaxes(showgrid=True, gridcolor='rgba(172,190,212,0.12)', zeroline=False)
    fig.update_yaxes(showgrid=False)
    return fig


def header(title, subtitle, eyebrow='GESTÃO DE ENGENHARIA'):
    st.markdown(
        '<div class="header-panel">'
        f'<div class="eyebrow">⚡ {escape(eyebrow)}</div>'
        f'<div class="hero-title">{escape(title)}</div>'
        f'<p class="hero-subtitle">{escape(subtitle)}</p>'
        '</div>', unsafe_allow_html=True,
    )


def logout():
    st.session_state.pop('role', None)
    st.session_state.pop('login_errors', None)
    st.rerun()


def login_page():
    a, mid, b = st.columns([1, 1.4, 1])
    with mid:
        st.write('')
        st.write('')
        header('Transforma | Engenharia',
               'Gestão de contrato e acompanhamento técnico • Mothé Engenharia',
               'ACESSO AO PAINEL')
        if demo_mode():
            st.info('Modo de avaliação: carregue seu próprio Excel e experimente os lançamentos sem alterar o Google Sheets. Os dados de teste duram apenas nesta sessão.')
            if st.button('Entrar na demonstração', type='primary', use_container_width=True):
                st.session_state['role'] = 'admin'
                st.rerun()
            st.stop()
        client_hash = str(secret('CLIENT_PASSWORD_HASH', ''))
        admin_hash = str(secret('ADMIN_PASSWORD_HASH', ''))
        if not client_hash or not admin_hash:
            st.error('Configuração de acesso pendente. O administrador precisa cadastrar as senhas em Secrets.')
            st.stop()
        if st.session_state.get('login_errors', 0) >= 6:
            st.error('Muitas tentativas nesta sessão. Feche a aba e procure o administrador.')
            st.stop()
        with st.form('login_form'):
            pwd = st.text_input('Senha de acesso', type='password', placeholder='Digite sua senha')
            send = st.form_submit_button('Entrar no painel', type='primary', use_container_width=True)
        if send:
            if verify_password(pwd, admin_hash):
                st.session_state['role'] = 'admin'
            elif verify_password(pwd, client_hash):
                st.session_state['role'] = 'cliente'
            else:
                st.session_state['login_errors'] = st.session_state.get('login_errors', 0) + 1
                st.error('Senha incorreta.')
                st.stop()
            st.rerun()
        st.caption('Acesso do cliente: consulta. Acesso administrativo: consulta e edição.')
    st.stop()


if not st.session_state.get('role'):
    login_page()

if st.session_state.pop('save_success', False):
    st.toast('Lançamento de teste registrado nesta sessão.' if demo_mode() else 'Dados salvos na planilha Google Sheets.', icon='✅')

try:
    raw = load_all()
    all_task_records = task_frame(raw['tasks'])
    tasks = activity_only_frame(all_task_records)
    diary = diary_frame(raw['diary'])
    visits = visit_frame(raw['visits'])
except Exception as exc:
    st.error('Não foi possível carregar os dados. Confirme o compartilhamento da planilha e as configurações da conexão.')
    if st.session_state.get('role') == 'admin':
        with st.expander('Detalhes técnicos (administrador)'):
            st.code(f'{type(exc).__name__}: {str(exc)}')
    if st.button('Tentar novamente'):
        clear_data_cache()
        st.rerun()
    st.stop()

today = today_brazil()
start_setting = str(secret('CONTRACT_START', '2026-09-01'))
try:
    contract_start, contract_end = contract_window(start_setting, today)
except ValueError:
    contract_start, contract_end = contract_window('2026-09-01', today)

if raw['visit_mode'] == 'registro':
    contract_visits = visits_from_register(visits, contract_start, contract_end, today)
else:
    contract_visits = visits_from_tasks(all_task_records, contract_start, contract_end, today)
contract = contract_metrics(contract_visits)

with st.sidebar:
    logo = Path(__file__).parent / 'Mothé Eng. Logo.png'
    if logo.is_file():
        st.image(str(logo), width=92)
    st.markdown('**⚡ Mothé Engenharia**')
    st.caption('TRANSFORMA • GESTÃO DE ENGENHARIA')
    st.divider()
    st.markdown('**🔎 Buscar e filtrar**')
    search = st.text_input('Buscar', placeholder='ID, descrição, local, pendência...', key='search_sidebar')
    base_opts = sorted([b for b in tasks['Base'].unique() if b])
    bases = st.multiselect('Base/unidade', base_opts, default=base_opts, key='base_sidebar')
    kind_opts = sorted([k for k in tasks['Tipo de Registro'].unique() if k])
    kinds = st.multiselect('Tipo de registro', kind_opts, default=kind_opts, key='kind_sidebar')
    status_opts = sorted([x for x in tasks['Status'].unique() if x])
    statuses = st.multiselect('Status', status_opts, default=status_opts, key='status_sidebar')
    with st.expander('Mais filtros (prioridade)'):
        priority_opts = sorted([x for x in tasks['Prioridade'].unique() if x])
        priorities = st.multiselect('Prioridade', priority_opts, default=priority_opts, key='priority_sidebar')
    st.divider()
    options = ['Visão executiva', 'Atividades e projetos', 'Visitas e contrato',
               'Planejamento e backlog', 'Histórico de atividades']
    if st.session_state['role'] == 'admin':
        options += ['Gestão administrativa']
    page = st.radio('Navegação', options, label_visibility='collapsed')

    if raw.get('demo'):
        st.divider()
        with st.expander('📁 Dados de teste / Importar Excel', expanded=not bool(st.session_state.get('demo_import_digest'))):
            st.caption('Importação local: nenhuma alteração é enviada ao Google Sheets.')
            up = st.file_uploader('Importar Excel do dashboard', type=['xlsx'], key='demo_xlsx_import')
            if up is not None:
                content = up.getvalue()
                digest = hashlib.sha256(content).hexdigest()
                if digest != st.session_state.get('demo_import_digest'):
                    try:
                        imported = parse_uploaded_workbook(content)
                        demo_replace_dataset(imported)
                        st.session_state['demo_import_digest'] = digest
                        st.rerun()
                    except ValueError as exc:
                        st.error(f'Falha ao carregar Excel: {exc}')
            st.caption(raw.get('source', 'Dados demonstrativos'))
            if st.button('Voltar aos dados fictícios', use_container_width=True):
                st.session_state.pop('demo_dataset', None)
                if up is not None:
                    st.session_state['demo_import_digest'] = hashlib.sha256(up.getvalue()).hexdigest()
                st.rerun()
        st.caption('⚠️ Demonstração: lançamentos não são gravados no Google.')
    st.divider()
    st.caption(f"Perfil: **{'Administrador' if st.session_state['role']=='admin' else 'Cliente'}**")
    if st.button('↻ Atualizar dados', use_container_width=True):
        clear_data_cache()
        st.rerun()
    if st.button('Sair da conta', use_container_width=True):
        logout()


filtered = tasks[
    tasks['Base'].isin(bases) & tasks['Status'].isin(statuses)
    & tasks['Prioridade'].isin(priorities) & tasks['Tipo de Registro'].isin(kinds)
].copy()
if search.strip():
    term = search.strip()
    key_fields = ['ID da Tarefa','Descrição','Pendências/Observações','Categoria','Subárea','Base']
    mask = pd.Series(False, index=filtered.index)
    for field in key_fields:
        mask |= filtered[field].str.contains(term, case=False, regex=False, na=False)
    filtered = filtered[mask].copy()
metrics = task_metrics(filtered, today)


def task_table(data):
    columns = ['ID da Tarefa','Descrição','Tipo de Registro','Base','Status',
               'Prioridade','Data de Início','Previsão de Conclusão']
    if data.empty:
        st.info('Nenhum registro para os filtros atuais.')
        return
    disp = sort_tasks_for_table(data)
    for col in columns:
        if col not in disp.columns: disp[col] = ''
    disp['Status'] = disp.apply(lambda r: display_status(r['Tipo de Registro'],r['Status']),axis=1)
    st.dataframe(disp[columns].rename(columns={
        'ID da Tarefa':'ID', 'Tipo de Registro':'Tipo',
        'Data de Início':'Início', 'Previsão de Conclusão':'Data de referência'}),
        hide_index=True, use_container_width=True, height=min(470, 40+35*len(disp)),
        column_config={
            'Descrição': st.column_config.TextColumn(width='large'),
            'Tipo': st.column_config.TextColumn(width='medium'),
            'Base': st.column_config.TextColumn(width='medium'),
            'Data de referência': st.column_config.TextColumn(width='small'),
        },
    )


def task_detail(data, key='details'):
    if data.empty:
        st.info('Não há atividades para esses filtros.')
        return
    ordered = data.sort_values('ID da Tarefa')
    options = ordered['ID da Tarefa'].tolist()
    def label(idx):
        r = ordered[ordered['ID da Tarefa'] == idx].iloc[0]
        return f"{idx} · {r['Descrição'][:75]}"
    chosen = st.selectbox('Abra uma atividade', options, format_func=label, key=key)
    r = ordered[ordered['ID da Tarefa'] == chosen].iloc[0]
    with st.container(border=True):
        a,b,c = st.columns([2,1,1])
        a.markdown(f"**{r['Descrição']}**")
        b.markdown(f"**Status:** {display_status(r['Tipo de Registro'],r['Status'])}")
        c.markdown(f"**Prioridade:** {r['Prioridade']}")
        st.caption(f"{r['Base']} • {r['Subárea']} • {r['Categoria']} • **{r['Tipo de Registro']}**")
        left,right = st.columns(2)
        left.write(f"**Início:** {format_date(r['Data de Início']) or 'A definir'}")
        left.write(f"**Fase atual:** {r['Fase'] or 'A definir'}")
        right.write(f"**Visita relacionada:** {format_date(r['Data da Visita']) or 'Não registrada'}")
        right.write(f"**Data de referência:** {format_date(r['Previsão de Conclusão']) or 'Sem data'}")
        st.caption(f"**Natureza do prazo:** {r['Condição do Prazo']}")
        if r['Motivo de Espera']:
            st.info(f"**Dependência registrada:** {r['Motivo de Espera']}")
        st.markdown('**Pendências e observações**')
        st.write(r['Pendências/Observações'] or 'Nenhuma observação registrada.')
        hist = diary[diary['ID da Tarefa'] == chosen].copy()
        st.markdown(f'**Histórico da atividade ({len(hist)} atualizações)**')
        if hist.empty:
            st.caption('Ainda não há atualizações no diário desta atividade.')
        else:
            hist['ordem'] = pd.to_datetime(hist['Data da Atualização_dt'],errors='coerce')
            hist = hist.sort_values('ordem', ascending=False)
            for _, event in hist.iterrows():
                st.markdown(f"**{format_date(event['Data da Atualização'])}** · {event['Fase Atualizada']} — {event['Status Atualizado']}")
                st.write(event['Descrição do que aconteceu'])
                st.divider()


def render_contract_progress():
    st.subheader('Presença técnica e cumprimento do contrato')
    st.caption(f'Ciclo: {contract_start:%d/%m/%Y} a {contract_end:%d/%m/%Y} • metas de 104 visitas em Macaé + 12 no Açu/Gradim')
    all_visits = contract['total']
    v1, v2, v3 = st.columns(3)
    v1.metric('Visitas realizadas (estimadas)' if raw['visit_mode']=='legado' else 'Visitas registradas', all_visits)
    v2.metric('Meta anual de visitas', 116)
    v3.metric('Visitas restantes', max(116-all_visits,0))
    left,right = st.columns(2)
    for col,label,value,goal in [
        (left,'Macaé/RJ',contract['macae'],104),
        (right,'Porto do Açu + Gradim',contract['inter'],12),
    ]:
        with col:
            with st.container(border=True):
                a,b=st.columns([3,1])
                a.markdown(f'**{label}**')
                b.markdown(f'**{pct(value,goal):.1f}%**')
                st.markdown(f'<div style="font-size:1.7rem;font-weight:800">{value} <span style="font-size:.96rem;color:#91A9C4">/ {goal} visitas</span></div>',unsafe_allow_html=True)
                st.progress(min(value/goal,1.0))
                st.caption(f'{max(goal-value,0)} visitas ainda previstas para essa base')
    if raw['visit_mode'] == 'legado':
        st.info('**Contagem provisória:** datas de visitas informadas nas tarefas, uma visita por base/dia. Um registro de rotina não cria uma visita contratual adicional. Confirme o histórico antes da auditoria.')
    else:
        imported_count = int(visits['Origem'].str.contains('Migração',case=False,na=False).sum())
        if imported_count:
            st.caption(f'{imported_count} registros migrados das atividades ainda precisam de validação documental.')


def contract_strip():
    """Cumprimento do contrato logo após o título, em uma única linha escaneável."""
    total=contract['total']
    st.markdown('### Presença técnica e contrato')
    rows=[
       ('Total de visitas',total,116,'no ciclo contratual'),
       ('Macaé',contract['macae'],104,'visitas na unidade'),
       ('Açu + Gradim',contract['inter'],12,'visitas nas demais bases'),
    ]
    cols=st.columns(3)
    for col,(label,n,goal,note) in zip(cols,rows):
        fraction=max(0,min(n/goal,1))
        with col:
            st.markdown('<div class="contract-strip">'
                f'<div class="contract-strip-title">{escape(label)}</div>'
                f'<div class="contract-strip-number">{n} <span style="font-size:.83rem;color:#93AFCE">/ {goal}</span></div>'
                f'<div class="mini-progress"><span style="width:{fraction*100:.1f}%"></span></div>'
                f'<div class="contract-strip-foot">{fraction*100:.1f}% cumpridos · faltam {max(goal-n,0)} · {escape(note)}</div>'
                '</div>',unsafe_allow_html=True)
    if raw['visit_mode']=='legado':
        st.caption('Contagem **provisória**, inferida das datas de visitas na planilha. Conta qualquer finalidade presencial, não apenas visita de rotina; uma visita por base/dia.')
    else:
        pending=int(visits['Validação'].eq('A validar').sum()) if 'Validação' in visits else 0
        st.caption(f'Visitas presenciais de todas as finalidades (rotina, emergência, reuniões e projetos). {pending} registros importados aguardam conferência.' if pending else 'Visitas presenciais de todas as finalidades, com um lançamento por base e data.')


def render_executive():
    header('Visão executiva | Transforma',
           'O contrato em números: presença em campo, entregas técnicas e próximas ações.')
    contract_strip()
    summary=delivery_overview(filtered,today)
    st.markdown('### Entregas de engenharia')
    cols=st.columns(4)
    items=[
        ('Concluídas',summary['done'],f"de {summary['deliveries']} entregas técnicas",'#35C99A'),
        ('Em execução',summary['active'],'serviços em andamento','#35A8E9'),
        ('Aguardando',summary['waiting'],'terceiros, materiais ou decisão','#F7B955'),
        ('No radar',summary['radar'],'demandas recebidas e planejadas','#A69BE9'),
    ]
    for col,(label,value,detail,accent) in zip(cols,items):
        with col: kpi_card(label,value,detail,accent)
    left,right=st.columns([1,1])
    with left:
        st.markdown('#### Entregas concluídas')
        st.caption('Lista completa com rolagem interna · últimas atividades no topo')
        closed=delivery_frame(filtered)
        closed=closed[closed['Status'].isin(CLOSED)]
        compact_table(closed,key='concluidas')
    with right:
        st.markdown('#### Prioridades atuais')
        st.caption('Entregas ainda abertas · acompanhe dependências e pendências')
        opened=delivery_frame(filtered)
        opened=opened[~opened['Status'].isin(CLOSED)]
        compact_table(opened,key='prioridades')
    with st.expander('Detalhamento: finalidades das visitas VIS e outras ações', expanded=False):
        subcols=st.columns(4)
        for col,(label,value,note) in zip(subcols,[
            ('Visitas de rotina',int(contract_visits['Finalidade'].eq('Rotina').sum()),'VIS classificados como rotina'),
            ('Reuniões',summary['meetings'],'alinhamentos registrados'),
            ('Emergências técnicas',summary['emergencies'],'prioridade emergencial'),
            ('Acompanhamentos',int(contract_visits['Finalidade'].isin(['Acompanhamento técnico','Levantamento/projeto']).sum()),'VIS técnicos e levantamentos'),
        ]):
            with col: kpi_card(label,value,note)
        st.caption('As visitas têm numeração VIS e são contadas por base/data. ACT identifica apenas demandas, projetos, serviços e registros de reunião separados.')
        distribution=filtered['Tipo de Registro'].value_counts().reset_index()
        distribution.columns=['Tipo','Registros']
        if not distribution.empty:
            fig=px.bar(distribution,x='Registros',y='Tipo',orientation='h',text='Registros',color_discrete_sequence=['#35A8E9'])
            fig.update_layout(showlegend=False,xaxis_title='',yaxis_title='')
            st.plotly_chart(style_figure(fig,270),use_container_width=True)
    if summary['unclassified_kinds']:
        st.caption(f'{summary["unclassified_kinds"]} tipos históricos foram sugeridos automaticamente e ainda podem ser revisados na edição dos registros.')

def render_tasks():
    header('Atividades e projetos | ACT',
           'Serviços, projetos, reuniões independentes e demandas. As visitas ficam exclusivamente em VIS.',
           'ACOMPANHAMENTO TÉCNICO')
    st.caption('Esta lista não contém visitas. Para consultar cada ida às bases, abra **Visitas e contrato** e selecione seu registro VIS.')
    categories=['Entregas técnicas','Reuniões e gestão','Radar','Todos os registros ACT']
    scope=st.radio('Visualizar',categories,horizontal=True,key='task_scope')
    if scope=='Entregas técnicas':
        view=delivery_frame(filtered)
    elif scope=='Reuniões e gestão':
        view=filtered[filtered['Tipo de Registro'].eq('Reunião/alinhamento')]
    elif scope=='Radar':
        view=filtered[filtered.apply(is_radar,axis=1)]
    else:
        view=filtered
    a,b,c=st.columns(3)
    a.metric('Registros na seleção',len(view))
    b.metric('Concluídos / realizados',int(view['Status'].isin(CLOSED).sum()))
    c.metric('Ainda abertos',int((~view['Status'].isin(CLOSED)).sum()))
    task_table(view)
    st.subheader('Detalhes do registro')
    task_detail(view,'task_query')


def render_visits():
    header('Visitas e execução contratual',
           'Acompanhamento das visitas técnicas e evidências de atendimento por unidade.',
           'PRESENÇA EM CAMPO')
    render_contract_progress()
    st.caption('Uma ida presencial conta como visita contratual independentemente da finalidade: rotina, emergência, reunião, levantamento ou acompanhamento técnico.')
    st.subheader('Visitas contabilizadas no ciclo')
    if contract_visits.empty:
        st.info('Ainda não foram registradas visitas dentro do ciclo selecionado.')
    else:
        show = contract_visits.sort_values('Data', ascending=False).copy()
        show['Data'] = show['Data'].map(lambda x:x.strftime('%d/%m/%Y'))
        st.dataframe(show.rename(columns={'Grupo':'Agrupamento contratual','Origem':'Fonte','Finalidade':'Objetivo da visita'}),
                     hide_index=True,use_container_width=True)
    if not visits.empty:
        st.subheader('Relato geral das visitas')
        st.caption('O registro reúne o que aconteceu no dia em campo — inclusive orientações rápidas que não geraram uma atividade ACT.')
        selected_visits = visits.copy().sort_values('Data da Visita_dt', ascending=False, na_position='last')
        view_rows = {str(r['ID da Visita']):r.to_dict() for _,r in selected_visits.iterrows()}
        chosen_visit = st.selectbox(
            'Abra uma visita para ler o relato', list(view_rows),
            format_func=lambda key: f"{format_date(view_rows[key].get('Data da Visita'))} · {view_rows[key].get('Base','')} · {view_rows[key].get('Resumo','')[:65]}",
            key='visit_daily_notes')
        visit_record = view_rows[chosen_visit]
        with st.container(border=True):
            st.markdown(f"**{escape(str(visit_record.get('Resumo','Visita')))}**")
            st.caption(f"{format_date(visit_record.get('Data da Visita'))} · {visit_record.get('Base','')} · {visit_record.get('Finalidade','')} · {visit_record.get('Validação','')}")
            st.markdown('**O que foi realizado durante a visita**')
            st.write(visit_record.get('Observações') or 'Relato geral ainda não informado.')
            if visit_record.get('ID da Tarefa vinculada'):
                st.caption(f"Atividade relacionada: {visit_record['ID da Tarefa vinculada']}")

    st.subheader('Agenda de visitas vinculadas às atividades')
    future = tasks[tasks['Data da Visita_dt'].map(lambda d:d is not None and d > today)].copy()
    if future.empty:
        st.info('Não há datas de visita futura na planilha de atividades.')
    else:
        future = future.sort_values('Data da Visita_dt')
        st.dataframe(future[['ID da Tarefa','Data da Visita','Base','Descrição']],hide_index=True,use_container_width=True)



def render_planning():
    header('Planejamento e backlog',
           'Demandas já recebidas, ainda sem tratamento completo, e dependências externas.',
           'ORGANIZAÇÃO DO TRABALHO')
    planned = filtered[filtered.apply(is_radar,axis=1)].copy()
    open_tasks = delivery_frame(filtered)
    open_tasks=open_tasks[~open_tasks['Status'].isin(CLOSED)].copy()
    waiting = open_tasks[open_tasks['Status'].isin(WAITING_STATUSES)].copy()
    committed = open_tasks[open_tasks['Condição do Prazo'].eq('Compromisso confirmado')].copy()
    next_deadlines = committed[committed['Previsão de Conclusão_dt'].map(
        lambda d: d is not None and today <= d <= today + pd.Timedelta(days=45))].copy()
    late = committed[committed['Previsão de Conclusão_dt'].map(
        lambda d: d is not None and d < today)].copy()
    a,b,c,d = st.columns(4)
    a.metric('Demandas no radar',len(planned))
    b.metric('Entregas técnicas abertas',len(open_tasks))
    c.metric('Aguardando / bloqueadas',len(waiting))
    d.metric('Compromissos vencidos',len(late))
    st.subheader('Demandas recebidas, ainda no radar')
    task_table(planned)
    st.subheader('Demandas aguardando terceiros, cliente ou materiais')
    if waiting.empty:
        st.info('Nenhum bloqueio identificado nos filtros.')
    else:
        waiting_table=waiting[['ID da Tarefa','Descrição','Status','Motivo de Espera','Base']].copy()
        waiting_table.columns=['ID','Descrição','Situação','Dependência registrada','Base']
        st.dataframe(waiting_table,hide_index=True,use_container_width=True,
                     column_config={'Descrição':st.column_config.TextColumn(width='large'),
                                    'Dependência registrada':st.column_config.TextColumn(width='large')})
    st.subheader('Prazos com compromisso confirmado (45 dias)')
    task_table(next_deadlines)
    st.caption('Datas são opcionais. Estimativas internas, prazos dependentes de terceiros e datas históricas não classificadas **não são tratados como descumprimento confirmado**.')


def render_diary():
    header('Histórico de atividades',
           'Atualizações, decisões e intervenções por atividade, com histórico preservado.',
           'RASTREABILIDADE')
    if diary.empty:
        st.info('Nenhum lançamento disponível.')
        return
    names=dict(zip(tasks['ID da Tarefa'],tasks['Descrição']))
    ids=sorted([x for x in diary['ID da Tarefa'].unique() if x])
    selected=st.selectbox('Filtrar por atividade', ['Todas as atividades']+ids,
                          format_func=lambda k: k if k=='Todas as atividades' else f"{k} · {names.get(k,'Atividade não localizada')[:75]}")
    scoped=diary if selected=='Todas as atividades' else diary[diary['ID da Tarefa']==selected]
    scoped=scoped.copy().sort_values('Data da Atualização_dt',ascending=False,na_position='last')
    c1,c2=st.columns([3,1])
    c1.caption(f'{len(scoped)} lançamentos encontrados • mais recentes primeiro')
    size=10
    max_pages=max(1,(len(scoped)+size-1)//size)
    with c2:
        page_index=st.number_input('Página',min_value=1,max_value=max_pages,value=1,step=1)
    for _,r in scoped.iloc[(page_index-1)*size:page_index*size].iterrows():
        task_id=r['ID da Tarefa']
        title=names.get(task_id,'Descrição não encontrada na base')
        snippet=str(r['Descrição do que aconteceu']).strip()
        event_name=f"{format_date(r['Data da Atualização'])}  •  {task_id} — {title[:62]}"
        with st.expander(event_name,expanded=False):
            st.caption(f"{r['Fase Atualizada'] or 'Fase não informada'} • {r['Status Atualizado'] or 'Status não informado'}")
            st.write(snippet or 'Sem texto informado.')
    st.caption('Abra uma atualização para ler o relato completo. Cada lançamento mantém vínculo com o ID original da planilha.')


def choice(label, options, default='', key=None):
    unique = list(dict.fromkeys([v for v in options if str(v).strip()]))
    if default and default not in unique:
        unique.append(default)
    return st.selectbox(label,unique,index=unique.index(default) if default in unique else 0,key=key)


def date_value(value, fallback=None):
    return parse_date(value) or fallback or today


def _commit(callable_fn, *args, **kwargs):
    try:
        result = callable_fn(*args, **kwargs)
        st.session_state['save_success'] = True
        clear_data_cache()
        st.rerun()
    except Exception as exc:
        st.error(f'Não foi possível salvar: {exc}')


def admin_new_task():
    st.markdown('#### Nova atividade')
    st.caption('Aqui você cadastra somente ACT (serviços, projetos, reuniões independentes e radar). Para registrar uma visita, selecione **Registrar visita** e receba um ID VIS.')
    with st.form('new_task',clear_on_submit=True):
        start_date=st.date_input('Data de início da atividade',today,format='DD/MM/YYYY')
        a,b,c=st.columns(3)
        base=a.selectbox('Base',BASES)
        subarea=b.text_input('Subárea',value='Geral')
        category=c.selectbox('Categoria',CATEGORIES)
        kind=st.selectbox('Tipo de registro ACT',ACT_KIND_OPTIONS,index=0,help='Presença em campo não é ACT; use o formulário VIS.')
        description=st.text_input('Descrição objetiva da atividade',max_chars=230)
        a,b,c=st.columns(3)
        phase=a.selectbox('Fase',PHASES,index=0)
        priority=b.selectbox('Prioridade',PRIORITIES)
        status=c.selectbox('Situação atual',STATUSES,index=0)
        has_deadline=st.checkbox('Informar prazo de conclusão?',value=False)
        deadline=st.date_input('Previsão de conclusão',today,format='DD/MM/YYYY',disabled=not has_deadline)
        deadline_kind=st.selectbox('Natureza da data / compromisso',DEADLINE_KINDS,index=0,
            help='Estimativa não é promessa. Só Compromisso confirmado entra no indicador de atraso contratual.')
        waiting_reason=st.text_area('Dependência externa / motivo da espera (opcional)',height=75)
        notes=st.text_area('Pendências / observações de campo',height=130)
        submit=st.form_submit_button('Cadastrar atividade',type='primary',use_container_width=True)
    if submit:
        if not description.strip():
            st.error('Preencha a descrição.')
        elif not subarea.strip():
            st.error('Preencha a subárea.')
        elif description.strip().casefold().startswith('visita'):
            st.error('Registre a visita em Registrar visita (VIS), não como atividade ACT.')
        else:
            row={'Data de Início':format_date(start_date),
                 'Data da Visita':'',
                 'Base':base,'Subárea':subarea,'Categoria':category,
                 'Descrição':description,'Fase':phase,'Prioridade':priority,
                 'Previsão de Conclusão':format_date(deadline) if has_deadline else '',
                 'Status':('Realizado' if status=='Resolvido' and kind!='Atividade técnica' else status),'Pendências/Observações':notes,
                 'Tipo de Registro':kind,'Condição do Prazo':deadline_kind,
                 'Motivo de Espera':waiting_reason}
            _commit(create_task,row)


def admin_edit_task():
    st.markdown('#### Editar atividade existente')
    if tasks.empty:
        st.info('Nenhuma atividade cadastrada.')
        return
    ids=sorted(tasks['ID da Tarefa'].tolist())
    ids_to_labels=dict(zip(tasks['ID da Tarefa'],tasks['Descrição']))
    chosen=st.selectbox('Atividade a alterar',ids,format_func=lambda v:f"{v} · {ids_to_labels.get(v,'')[:75]}", key='admin_edit_select')
    row=tasks[tasks['ID da Tarefa']==chosen].iloc[0].to_dict()
    previous={col: row.get(col,'') for col in ALL_TASK_COLUMNS}
    with st.form(f'edit_{chosen}'):
        a,b,c=st.columns(3)
        start=a.date_input('Data de início',date_value(row['Data de Início']),format='DD/MM/YYYY')
        has_visit=b.checkbox('Possui data de visita?',value=bool(parse_date(row['Data da Visita'])))
        visit_date=c.date_input('Data de visita',date_value(row['Data da Visita']),format='DD/MM/YYYY',disabled=not has_visit)
        a,b,c=st.columns(3)
        base=choice('Base',BASES,row['Base'])
        subarea=b.text_input('Subárea',value=row['Subárea'])
        with c:
            category=choice('Categoria',CATEGORIES,row['Categoria'])
        with st.container():
            kind=choice('Tipo de registro ACT',ACT_KIND_OPTIONS,row['Tipo de Registro'])
        description=st.text_input('Descrição',value=row['Descrição'])
        a,b,c=st.columns(3)
        with a: phase=choice('Fase',PHASES,row['Fase'])
        with b: priority=choice('Prioridade',PRIORITIES,row['Prioridade'])
        with c: status=choice('Status',STATUSES,row['Status'])
        has_deadline=st.checkbox('Tem previsão de conclusão?',value=bool(parse_date(row['Previsão de Conclusão'])))
        deadline=st.date_input('Previsão de conclusão',date_value(row['Previsão de Conclusão']),format='DD/MM/YYYY',disabled=not has_deadline)
        with st.container():
            deadline_kind=choice('Natureza do prazo',DEADLINE_KINDS,row['Condição do Prazo'])
        waiting_reason=st.text_area('Dependência externa / motivo da espera',value=row['Motivo de Espera'],height=85)
        notes=st.text_area('Pendências / observações',value=row['Pendências/Observações'],height=150)
        submit=st.form_submit_button('Salvar alterações',type='primary',use_container_width=True)
    if submit:
        if not description.strip():
            st.error('A descrição é obrigatória.')
            return
        data={**previous,'Data de Início':format_date(start),
              'Data da Visita':format_date(visit_date) if has_visit else '',
              'Base':base,'Subárea':subarea,'Categoria':category,
              'Descrição':description,'Fase':phase,'Prioridade':priority,
              'Previsão de Conclusão':format_date(deadline) if has_deadline else '',
              'Status':('Realizado' if status=='Resolvido' and kind!='Atividade técnica' else status),'Pendências/Observações':notes,
              'Tipo de Registro':kind,'Condição do Prazo':deadline_kind,
              'Motivo de Espera':waiting_reason}
        _commit(update_task,chosen,previous,data)


def admin_diary():
    st.markdown('#### Registrar atualização da atividade')
    st.caption('Informe o que você fez hoje em uma tarefa existente. Você pode também atualizar a fase e o status no mesmo lançamento.')
    if tasks.empty:
        st.warning('Cadastre ao menos uma atividade primeiro.')
        return
    ids=sorted(tasks['ID da Tarefa'].tolist())
    ids_to_labels=dict(zip(tasks['ID da Tarefa'],tasks['Descrição']))
    chosen=st.selectbox('ID vinculado',ids,format_func=lambda v:f"{v} · {ids_to_labels.get(v,'')[:80]}",key='admin_diary_select')
    t=tasks[tasks['ID da Tarefa']==chosen].iloc[0]
    st.caption(t['Descrição'])
    with st.form(f'add_diary_{chosen}',clear_on_submit=True):
        dt=st.date_input('Data da atualização',today,format='DD/MM/YYYY')
        a,b=st.columns(2)
        with a: phase=choice('Fase após esta atualização',PHASES,t['Fase'])
        with b: status=choice('Status após esta atualização',STATUSES,t['Status'])
        text=st.text_area('O que aconteceu? Decisões, ações, próximos passos e pendências',height=180)
        waiting_reason=st.text_area('Dependência / bloqueio (se houver)',value=t['Motivo de Espera'],height=80,help='Ex.: aguardando cotação do fornecedor. Atualiza a ficha quando a sincronização está marcada.')
        sync=st.checkbox('Atualizar também fase e status na atividade',value=True)
        submit=st.form_submit_button('Salvar no diário de bordo',type='primary',use_container_width=True)
    if submit:
        if not text.strip():
            st.error('Descreva o que aconteceu.')
        else:
            record={'Data da Atualização':format_date(dt),'ID da Tarefa':chosen,
                    'Fase Atualizada':phase,'Status Atualizado':('Realizado' if status=='Resolvido' and t['Tipo de Registro']!='Atividade técnica' else status),
                    'Descrição do que aconteceu':text}
            _commit(add_diary_and_update,record,sync,waiting_reason)


def admin_visit():
    st.markdown('#### Registrar visita do contrato — ID VIS automático')
    st.caption('Cada presença na base recebe VIS (nunca ACT). Registre no relato todas as orientações, consultorias, reuniões e serviços breves, mesmo sem abrir uma atividade técnica.')
    if raw['visit_mode'] == 'legado':
        st.warning('A base ainda não possui a aba Visitas_Contrato. Você pode migrar as datas e os relatos históricos das atividades antes de cadastrar visitas.')
        checked = st.checkbox('Entendo que as visitas importadas são estimadas e precisam ser validadas.')
        if st.button('Simular migração de visitas e relatos' if demo_mode() else 'Criar aba e importar visitas e relatos',
                     disabled=not checked, type='primary'):
            _commit(initialize_visits_from_tasks, raw['tasks'])
        return

    modes = ['Registrar nova visita']
    if not visits.empty:
        modes.append('Complementar / validar visita existente')
    mode = st.radio('O que deseja fazer?', modes, horizontal=True, key='visit_action')

    if mode == 'Complementar / validar visita existente':
        ordered = visits.sort_values('Data da Visita_dt', ascending=False, na_position='last')
        lookup = {str(row['ID da Visita']): row.to_dict() for _,row in ordered.iterrows()}
        ids = list(lookup)
        def name_of(visit_id):
            rec = lookup[visit_id]
            return f"{format_date(rec.get('Data da Visita'))} · {rec.get('Base','')} · {visit_id} · {rec.get('Resumo','')[:48]}"
        chosen = st.selectbox('Selecione a visita já registrada', ids, format_func=name_of, key='visit_edit_id')
        rec = lookup[chosen]
        st.caption(f"Base: {rec.get('Base','')} · data: {format_date(rec.get('Data da Visita'))} · origem: {rec.get('Origem','')}")
        with st.form(f'visit_edit_{chosen}'):
            summary = st.text_input('Assunto principal da visita', value=str(rec.get('Resumo','')), max_chars=250)
            observations = st.text_area(
                'Relato geral do dia — atividades, orientações, consultorias rápidas e reuniões',
                value=str(rec.get('Observações','')), height=260,
                help='Registre o que ocorreu durante a presença na unidade, mesmo quando não foi aberta uma tarefa ACT.')
            a,b = st.columns(2)
            purpose = a.selectbox('Finalidade predominante', VISIT_PURPOSES,
                                  index=VISIT_PURPOSES.index(rec.get('Finalidade')) if rec.get('Finalidade') in VISIT_PURPOSES else 0)
            options = ['A validar','Confirmada','Descartada']
            initial = rec.get('Validação', 'A validar')
            validation = b.selectbox('Conferência da visita',options,index=options.index(initial) if initial in options else 0,
                                     help='Confirme a ida somente após verificar o registro histórico.')
            responsible = st.text_input('Responsável', value=str(rec.get('Responsável','')))
            submit = st.form_submit_button('Salvar relato da visita', type='primary', use_container_width=True)
        if submit:
            if not summary.strip() or not observations.strip():
                st.error('Informe o assunto e o relato geral antes de salvar.')
            else:
                previous={col:rec.get(col,'') for col in ALL_VISIT_COLUMNS}
                changes={'Resumo':summary,'Observações':observations,'Finalidade':purpose,
                         'Validação':validation,'Responsável':responsible}
                _commit(update_visit,chosen,previous,changes)
        return

    with st.form('add_visit_form', clear_on_submit=True):
        a,b,c = st.columns(3)
        dt = a.date_input('Data da visita',today,format='DD/MM/YYYY')
        base = b.selectbox('Base visitada',BASES[:-1])
        tipo = c.selectbox('Tipo de atendimento',['Presencial','Remoto'])
        purpose = st.selectbox('Finalidade predominante', VISIT_PURPOSES,
                               help='Rotina, emergência, levantamento, reunião ou acompanhamento; a finalidade não altera a contagem contratual.')
        related = st.selectbox('Atividade vinculada (opcional)', ['Sem vínculo']+sorted(tasks['ID da Tarefa'].tolist()))
        summary = st.text_input('Assunto principal / objetivo da visita',max_chars=250)
        observations = st.text_area(
            'Relato geral do dia — o que foi feito, inclusive consultorias rápidas e orientações',
            height=260, placeholder='Descreva de forma objetiva os serviços, conversas técnicas, reuniões, decisões e acompanhamentos realizados na visita...',
            help='Não é necessário criar uma atividade ACT para cada orientação breve. Este relato pertence à visita.')
        responsible = st.text_input('Responsável',value='Mothé Engenharia')
        submit = st.form_submit_button('Registrar visita e relato geral',type='primary',use_container_width=True)
    if submit:
        if not summary.strip() or not observations.strip():
            st.error('Preencha o assunto principal e o relato geral da visita.')
        elif dt > today and tipo == 'Presencial':
            st.error('Registre visitas futuras na agenda; contabilize apenas as que já aconteceram.')
        else:
            record={'Data da Visita':format_date(dt),'Base':base,'Tipo':tipo,
                    'ID da Tarefa vinculada':'' if related=='Sem vínculo' else related,
                    'Resumo':summary,'Observações':observations,
                    'Responsável':responsible,'Origem':'Registro manual',
                    'Finalidade':purpose,'Validação':'Confirmada'}
            _commit(add_visit,record)


def admin_quality():
    st.markdown('#### Conferência de registros e exportação')
    st.caption('Este espaço mostra cadastros incompletos e permite exportar os dados; atualizações históricas de fase/status são normais e não são erros.')
    q=quality_issues(tasks)
    a,b,c=st.columns(3)
    a.metric('Cadastros que merecem conferência',len(q))
    b.metric('Tipos históricos a conferir',int(tasks['Tipo inferido'].sum()))
    c.metric('Total de registros no diário',len(diary))
    if not q.empty:
        st.dataframe(q,hide_index=True,use_container_width=True)
    else:
        st.success('Não foram identificadas inconsistências pelas regras atuais.')
    st.caption('O histórico de fases/status de uma mesma atividade é mantido normalmente. O status atual é a última situação declarada na ficha, enquanto o histórico mostra as transições. Tipos inferidos podem ser revisados individualmente.')
    def csv_export(df):
        out=io.StringIO()
        copy=df.copy()
        for col in copy.columns:
            copy[col]=copy[col].map(lambda x: ("'"+x) if isinstance(x,str) and x.lstrip().startswith(('=','+','-','@')) else x)
        copy.to_csv(out,index=False)
        return ('\ufeff'+out.getvalue()).encode('utf-8')
    a,b=st.columns(2)
    a.download_button('Exportar atividades (CSV)',csv_export(tasks[ALL_TASK_COLUMNS]),
                      file_name='transforma_atividades.csv',mime='text/csv',use_container_width=True)
    b.download_button('Exportar diário (CSV)',csv_export(diary[DIARY_COLUMNS]),
                      file_name='transforma_diario.csv',mime='text/csv',use_container_width=True)


def admin_today():
    st.markdown('### 📝 Lançar o trabalho realizado no dia')
    st.caption('Atualize um serviço ACT, cadastre uma nova atividade ACT ou registre a presença/relato de campo como visita VIS. Não é necessário criar ACT para acompanhar uma visita.')
    action = st.radio('O trabalho é de uma atividade já cadastrada?',
                      ['Atualizar atividade ACT', 'Cadastrar nova atividade ACT', 'Registrar visita VIS'],
                      key='admin_today_kind')
    st.divider()
    if action == 'Atualizar atividade ACT':
        admin_diary()
    elif action == 'Cadastrar nova atividade ACT':
        admin_new_task()
    else:
        admin_visit()


def render_admin():
    header('Central de gestão',
           'Registre o trabalho do dia e acompanhe as demandas sem abrir a planilha.',
           'ÁREA EXCLUSIVA • ADMINISTRADOR')
    st.caption('Na primeira gravação real, os novos campos de tipo, prazo e dependência serão acrescentados após as colunas originais do Google Sheets; nenhum dado antigo será reescrito em massa.')
    if raw.get('demo'):
        st.warning('**Modo de teste ativo:** os formulários estão liberados. As alterações são apenas nesta sessão, aparecem nos indicadores e podem ser exportadas; não modificam sua planilha Google.')
    elif not google_ready():
        st.warning('Edição indisponível até configurar a conta Google Sheets em Streamlit Secrets.')
        admin_quality()
        return
    admin_pages = ['📝 Lançar trabalho do dia', '＋ Nova atividade', '✎ Editar atividade',
                   '▤ Atualizações', '◉ Registrar visita', '✓ Conferência / Exportação']
    action = st.radio('Escolha uma operação', admin_pages, horizontal=True,
                      label_visibility='collapsed', key='admin_action')
    st.write('')
    if action == admin_pages[0]: admin_today()
    elif action == admin_pages[1]: admin_new_task()
    elif action == admin_pages[2]: admin_edit_task()
    elif action == admin_pages[3]: admin_diary()
    elif action == admin_pages[4]: admin_visit()
    else: admin_quality()

if page=='Visão executiva':
    render_executive()
elif page=='Atividades e projetos':
    render_tasks()
elif page=='Visitas e contrato':
    render_visits()
elif page=='Planejamento e backlog':
    render_planning()
elif page=='Histórico de atividades':
    render_diary()
elif page=='Gestão administrativa' and st.session_state['role']=='admin':
    render_admin()

st.divider()
st.caption('Mothé Engenharia • Painel Transforma • Dados reais atualizados a cada 45 segundos; na demonstração, as informações são locais à sessão e não alteram o Google Sheets.')

