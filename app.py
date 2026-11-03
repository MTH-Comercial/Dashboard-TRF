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
    TASK_COLUMNS, DIARY_COLUMNS, VISIT_COLUMNS,
    contract_metrics, contract_window, diary_frame, format_date,
    location_group, pct, quality_issues, task_frame, task_metrics,
    visit_frame, visits_from_register, visits_from_tasks, parse_date, today_brazil,
)
from security import verify_password
from preview import parse_uploaded_workbook
from storage import (
    add_diary_and_update, add_visit, create_task, demo_mode, google_ready,
    initialize_visits_from_tasks, load_all, secret, update_task,
    clear_data_cache, demo_replace_dataset,
)

st.set_page_config(
    page_title='Transforma | Painel de Engenharia', page_icon='⚡',
    layout='wide', initial_sidebar_state='expanded',
)

# UI theme — input controls and charts remain native, accessible Streamlit widgets.
st.markdown('''<style>
.block-container { max-width: 1500px; padding-top: 1.65rem; padding-bottom: 3rem; }
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
  margin: 0 0 22px 0;
}
.eyebrow { color: #74BDE9; text-transform: uppercase; letter-spacing: .13em;
  font-weight: 800; font-size: .72rem; margin-bottom: 6px; }
.hero-title { font-size: clamp(1.6rem,3vw,2.2rem); font-weight: 800; color: #F4F8FE;
  letter-spacing: -.035em; margin: 0 0 4px 0; }
.hero-subtitle { color: #B0C3DA; font-size: .93rem; margin: 0; }
.section-note { font-size: .81rem; color: #92A9C5; margin-bottom: .65rem; }
.soft-badge { border-radius: 20px; padding: 3px 10px; background: #183A54;
  color: #88D1FF; font-size: .78rem; }
</style>''', unsafe_allow_html=True)

COLOR_STATUS = {
    'Resolvido': '#35C99A', 'Em Andamento': '#35A8E9',
    'Pausado': '#F7B955', 'Aguardando Terceiros': '#EA7386',
    'Aguardando Terceiro/Compras': '#EA7386', 'Aguardando': '#F7B955',
    'Não Iniciado': '#8D9EB5', 'Agendado': '#B095EC',
}
PLOT_FONT = dict(family='Inter, Arial, sans-serif', color='#C8D6E8', size=12)


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
    tasks = task_frame(raw['tasks'])
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
    contract_visits = visits_from_tasks(tasks, contract_start, contract_end, today)
contract = contract_metrics(contract_visits)

with st.sidebar:
    logo = Path(__file__).parent / 'Mothé Eng. Logo.png'
    if logo.is_file():
        st.image(str(logo), width=165)
    st.markdown('### ⚡ Mothé Engenharia')
    st.caption('PAINEL TRANSFORMA • VERSÃO 2.0')
    if raw.get('demo'):
        st.warning('Ambiente demonstrativo · sem gravação no Google')
        st.markdown('#### Carregar seus dados reais')
        st.caption('Baixe sua planilha Google em Arquivo → Fazer download → Microsoft Excel (.xlsx) e carregue aqui. A importação é temporária e individual nesta sessão.')
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
                    st.error(f'Falha ao carregar o Excel: {exc}')
        st.caption(raw.get('source', 'Dados de exemplo'))
        if st.button('Voltar aos dados fictícios', use_container_width=True):
            st.session_state.pop('demo_dataset', None)
            if up is not None:
                st.session_state['demo_import_digest'] = hashlib.sha256(up.getvalue()).hexdigest()
            st.rerun()

    st.divider()
    options = ['Visão executiva', 'Atividades e projetos', 'Visitas e contrato', 'Planejamento e backlog', 'Diário de bordo']
    if st.session_state['role'] == 'admin':
        options += ['Gestão administrativa']
    page = st.radio('Navegação', options, label_visibility='collapsed')
    st.divider()
    st.markdown('**Filtros das atividades**')
    base_opts = sorted([b for b in tasks['Base'].unique() if b])
    bases = st.multiselect('Base/unidade', base_opts, default=base_opts)
    status_opts = sorted([s for s in tasks['Status'].unique() if s])
    statuses = st.multiselect('Status', status_opts, default=status_opts)
    priority_opts = sorted([p for p in tasks['Prioridade'].unique() if p])
    priorities = st.multiselect('Prioridade', priority_opts, default=priority_opts)
    search = st.text_input('Buscar atividade', placeholder='ID, descrição, local...')
    st.divider()
    st.caption(f"Perfil: **{'Administrador' if st.session_state['role']=='admin' else 'Cliente (consulta)'}**")
    if st.button('↻ Atualizar dados', use_container_width=True):
        clear_data_cache()
        st.rerun()
    if st.button('Sair da conta', use_container_width=True):
        logout()

filtered = tasks[
    tasks['Base'].isin(bases) & tasks['Status'].isin(statuses)
    & tasks['Prioridade'].isin(priorities)
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
    columns = ['ID da Tarefa','Descrição','Base','Subárea','Status','Prioridade','Data de Início','Previsão de Conclusão']
    disp = data.copy()
    disp['Ordenação'] = pd.to_datetime(disp['Data de Início_dt'], errors='coerce')
    disp = disp.sort_values('Ordenação', ascending=False, na_position='last')
    st.dataframe(disp[columns].rename(columns={
        'ID da Tarefa':'ID', 'Data de Início':'Início',
        'Previsão de Conclusão':'Prazo'}), hide_index=True, use_container_width=True,
        column_config={'Descrição': st.column_config.TextColumn(width='large'),
                       'Base':st.column_config.TextColumn(width='medium')},
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
        b.markdown(f"**Status:** {r['Status']}")
        c.markdown(f"**Prioridade:** {r['Prioridade']}")
        st.caption(f"{r['Base']} • {r['Subárea']} • {r['Categoria']}")
        left,right = st.columns(2)
        left.write(f"**Início:** {format_date(r['Data de Início']) or 'A definir'}")
        left.write(f"**Fase atual:** {r['Fase'] or 'A definir'}")
        right.write(f"**Visita relacionada:** {format_date(r['Data da Visita']) or 'Não registrada'}")
        right.write(f"**Prazo:** {format_date(r['Previsão de Conclusão']) or 'Não informado'}")
        st.markdown('**Pendências e observações**')
        st.write(r['Pendências/Observações'] or 'Nenhuma observação registrada.')
        hist = diary[diary['ID da Tarefa'] == chosen].copy()
        st.markdown(f'**Diário de bordo ({len(hist)} atualizações)**')
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
    st.subheader('Cumprimento do contrato de visitas')
    st.caption(f'Ciclo: {contract_start:%d/%m/%Y} a {contract_end:%d/%m/%Y} • metas anuais 104 Macaé / 12 Gradim e Açu')
    left,right = st.columns(2)
    for col,label,value,goal in [
        (left,'Macaé/RJ',contract['macae'],104),
        (right,'Porto do Açu + Gradim',contract['inter'],12),
    ]:
        with col:
            with st.container(border=True):
                x,y = st.columns([3,1])
                x.markdown(f'**{label}**')
                y.markdown(f'**{pct(value,goal):.1f}%**')
                st.markdown(f'<div style="font-size:1.55rem;font-weight:800">{value} <span style="font-size:.95rem;color:#91A9C4">/ {goal} visitas</span></div>',unsafe_allow_html=True)
                st.progress(min(value/goal,1.0))
                st.caption(f'Faltam {max(goal-value,0)} visitas para a meta do ciclo')
    if raw['visit_mode'] == 'legado':
        st.info('**Contagem provisória:** visitas estimadas a partir das datas das atividades, sem registro independente. Uma visita por base/dia. O administrador pode migrar para o controle formal de visitas.')
    else:
        imported_count = int(visits['Origem'].str.contains('Migração',case=False,na=False).sum())
        if imported_count:
            st.caption(f'{imported_count} lançamentos históricos foram migrados das atividades e ainda precisam de validação documental.')


def render_executive():
    header('Visão executiva | Transforma',
           'Panorama do contrato, entregas, demandas em aberto e atuação técnica por unidade.')
    st.caption('Os indicadores de tarefas respeitam os filtros da barra lateral. As visitas contratuais consideram todas as bases do ciclo.')
    cols=st.columns(5)
    for col,label,value,detail in [
        (cols[0],'Atividades', metrics['total'],'escopo filtrado'),
        (cols[1],'Resolvidas',metrics['resolved'],f"{metrics['resolution_rate']:.0%} de resolução"),
        (cols[2],'Em andamento',metrics['ongoing'],'tarefas ativas'),
        (cols[3],'Emergenciais',metrics['emergencies'],'prioridade emergencial'),
        (cols[4],'Prazos vencidos',metrics['overdue'],'não resolvidas'),
    ]:
        with col:
            st.metric(label, value)
            st.caption(detail)
    st.write('')
    render_contract_progress()
    st.write('')
    st.subheader('Onde está concentrado o trabalho')
    first,second = st.columns([1,1.25])
    with first:
        with st.container(border=True):
            st.markdown('**Situação das atividades**')
            statuses = filtered['Status'].value_counts().reset_index()
            statuses.columns = ['Status','Quantidade']
            if statuses.empty:
                st.info('Nenhum dado com os filtros escolhidos.')
            else:
                fig = px.bar(statuses, x='Quantidade',y='Status',orientation='h',
                             color='Status',color_discrete_map=COLOR_STATUS,text='Quantidade')
                fig.update_yaxes(categoryorder='total ascending')
                fig.update_layout(showlegend=False,xaxis_title='',yaxis_title='')
                st.plotly_chart(style_figure(fig,315),use_container_width=True)
    with second:
        with st.container(border=True):
            st.markdown('**Atuação por categoria de engenharia**')
            category = filtered.groupby(['Categoria','Status'], as_index=False).size().rename(columns={'size':'Atividades'})
            if category.empty:
                st.info('Nenhum dado com os filtros escolhidos.')
            else:
                fig = px.bar(category,x='Atividades',y='Categoria',orientation='h',
                             color='Status',color_discrete_map=COLOR_STATUS,barmode='stack')
                fig.update_yaxes(categoryorder='total ascending')
                fig.update_layout(xaxis_title='',yaxis_title='',legend=dict(orientation='h', y=-.27))
                st.plotly_chart(style_figure(fig,315),use_container_width=True)
    st.subheader('Evolução dos atendimentos')
    left,right = st.columns([1.25,1])
    with left:
        with st.container(border=True):
            st.markdown('**Atividades iniciadas por mês**')
            valid = filtered[filtered['Data de Início_dt'].notna()].copy()
            if valid.empty:
                st.info('Datas insuficientes para desenhar o gráfico.')
            else:
                valid['Mês'] = valid['Data de Início_dt'].map(lambda x:x.strftime('%Y-%m'))
                trend = valid.groupby('Mês', as_index=False).size().rename(columns={'size':'Atividades'})
                fig = px.bar(trend,x='Mês',y='Atividades',text='Atividades',
                             color_discrete_sequence=['#35A8E9'])
                fig.update_layout(xaxis_title='',yaxis_title='Atividades iniciadas')
                st.plotly_chart(style_figure(fig,300),use_container_width=True)
                st.caption('O gráfico usa a data de início, não a data de conclusão — que ainda não consta na base.')
    with right:
        with st.container(border=True):
            st.markdown('**Demandas que merecem atenção**')
            open_tasks = filtered[~filtered['Status'].isin(CLOSED)].copy()
            if open_tasks.empty:
                st.success('Não há pendências abertas neste filtro.')
            else:
                overdue = open_tasks[open_tasks['Previsão de Conclusão_dt'].map(
                    lambda x: x is not None and x < today)]
                st.metric('Atividades abertas', len(open_tasks))
                st.metric('Com prazo vencido',len(overdue))
                st.metric('Sem prazo informado',int(open_tasks['Previsão de Conclusão_dt'].isna().sum()))
                if not overdue.empty:
                    st.markdown('**Prazos vencidos**')
                    for _,r in overdue.head(4).iterrows():
                        st.markdown(f"- **{r['ID da Tarefa']}** · {r['Descrição'][:70]}")
    st.write('')
    st.subheader('Atividades recentes')
    task_table(filtered.head(100))


def render_tasks():
    header('Atividades e projetos',
           'Consulta de serviços de engenharia, status, responsáveis pela execução e pendências documentadas.',
           'ACOMPANHAMENTO TÉCNICO')
    st.metric('Atividades encontradas',len(filtered))
    task_table(filtered)
    st.write('')
    task_detail(filtered,'task_query')


def render_visits():
    header('Visitas e execução contratual',
           'Acompanhamento das visitas técnicas e evidências de atendimento por unidade.',
           'PRESENÇA EM CAMPO')
    render_contract_progress()
    st.subheader('Visitas contabilizadas no ciclo')
    if contract_visits.empty:
        st.info('Ainda não foram registradas visitas dentro do ciclo selecionado.')
    else:
        show = contract_visits.sort_values('Data', ascending=False).copy()
        show['Data'] = show['Data'].map(lambda x:x.strftime('%d/%m/%Y'))
        st.dataframe(show.rename(columns={'Grupo':'Agrupamento contratual','Origem':'Fonte'}),
                     hide_index=True,use_container_width=True)
    st.subheader('Agenda de visitas vinculadas às atividades')
    future = tasks[tasks['Data da Visita_dt'].map(lambda d:d is not None and d > today)].copy()
    if future.empty:
        st.info('Não há datas de visita futura na planilha de atividades.')
    else:
        future = future.sort_values('Data da Visita_dt')
        st.dataframe(future[['ID da Tarefa','Data da Visita','Base','Descrição']],hide_index=True,use_container_width=True)



def render_planning():
    header('Planejamento e backlog',
           'Próximas demandas, pendências de engenharia e previsão de execução por base.',
           'ORGANIZAÇÃO DO TRABALHO')
    planned = filtered[
        filtered['Prioridade'].eq('Planejamento (Futuro)')
        | filtered['Data de Início_dt'].map(lambda d:d is not None and d > today)
    ].copy()
    open_tasks = filtered[~filtered['Status'].isin(CLOSED)].copy()
    next_deadlines = open_tasks[open_tasks['Previsão de Conclusão_dt'].map(
        lambda d:d is not None and today <= d <= today + pd.Timedelta(days=45))].copy()
    overdue = open_tasks[open_tasks['Previsão de Conclusão_dt'].map(
        lambda d:d is not None and d < today)].copy()
    a,b,c,d = st.columns(4)
    a.metric('No radar / planejamento',len(planned))
    b.metric('Pendentes de solução',len(open_tasks))
    c.metric('Prazos próximos (45 dias)',len(next_deadlines))
    d.metric('Prazos vencidos',len(overdue))
    st.subheader('Demandas planejadas ou futuras')
    if planned.empty:
        st.info('Nenhuma atividade de planejamento neste filtro.')
    else:
        task_table(planned)
    st.subheader('Prazos de conclusão nas próximas 6 semanas')
    if next_deadlines.empty:
        st.info('Não há prazo futuro registrado nos próximos 45 dias.')
    else:
        task_table(next_deadlines.sort_values('Previsão de Conclusão_dt'))
    st.caption('Atividades classificadas como Planejamento (Futuro) permanecem no radar até que sua prioridade seja revisada, mesmo se a data planejada estiver no passado.')

def render_diary():
    header('Diário de bordo',
           'Histórico cronológico de atividades, decisões de campo e evolução dos serviços.',
           'RASTREABILIDADE')
    if diary.empty:
        st.info('Nenhum lançamento disponível.')
        return
    ids = sorted([v for v in diary['ID da Tarefa'].unique() if v])
    selected = st.selectbox('Filtrar por tarefa', ['Todas as atividades']+ids)
    scoped = diary if selected=='Todas as atividades' else diary[diary['ID da Tarefa']==selected]
    scoped = scoped.copy()
    scoped['sort'] = pd.to_datetime(scoped['Data da Atualização_dt'], errors='coerce')
    scoped = scoped.sort_values('sort',ascending=False)
    st.caption(f'{len(scoped)} registros encontrados')
    for _,r in scoped.head(100).iterrows():
        with st.container(border=True):
            a,b = st.columns([1,3])
            a.markdown(f"**{format_date(r['Data da Atualização'])}**")
            a.caption(r['ID da Tarefa'])
            b.markdown(f"**{r['Fase Atualizada']}** · {r['Status Atualizado']}")
            b.write(r['Descrição do que aconteceu'])
    if len(scoped)>100:
        st.caption('Exibindo os 100 lançamentos mais recentes; filtre pelo ID para localizar mais.')


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
    st.caption('O ID é gerado automaticamente. Na demonstração, nenhuma alteração é gravada no Google Sheets.')
    with st.form('new_task',clear_on_submit=True):
        a,b,c = st.columns(3)
        start_date=a.date_input('Data de início',today,format='DD/MM/YYYY')
        has_visit=b.checkbox('Esta atividade inclui visita de campo?',value=False)
        visit_date=c.date_input('Data da visita (se aplicável)',today,format='DD/MM/YYYY',disabled=not has_visit)
        a,b,c=st.columns(3)
        base=a.selectbox('Base',BASES)
        subarea=b.text_input('Subárea',value='Geral')
        category=c.selectbox('Categoria',CATEGORIES)
        description=st.text_input('Descrição objetiva da atividade',max_chars=230)
        a,b,c=st.columns(3)
        phase=a.selectbox('Fase',PHASES,index=0)
        priority=b.selectbox('Prioridade',PRIORITIES)
        status=c.selectbox('Status',STATUSES,index=0)
        has_deadline=st.checkbox('Informar prazo de conclusão?',value=False)
        deadline=st.date_input('Previsão de conclusão',today,format='DD/MM/YYYY',disabled=not has_deadline)
        notes=st.text_area('Pendências / observações de campo',height=130)
        submit=st.form_submit_button('Cadastrar atividade',type='primary',use_container_width=True)
    if submit:
        if not description.strip():
            st.error('Preencha a descrição.')
        elif not subarea.strip():
            st.error('Preencha a subárea.')
        else:
            row={'Data de Início':format_date(start_date),
                 'Data da Visita':format_date(visit_date) if has_visit else '',
                 'Base':base,'Subárea':subarea,'Categoria':category,
                 'Descrição':description,'Fase':phase,'Prioridade':priority,
                 'Previsão de Conclusão':format_date(deadline) if has_deadline else '',
                 'Status':status,'Pendências/Observações':notes}
            _commit(create_task,row)


def admin_edit_task():
    st.markdown('#### Editar atividade existente')
    if tasks.empty:
        st.info('Nenhuma atividade cadastrada.')
        return
    ids=sorted(tasks['ID da Tarefa'].tolist())
    chosen=st.selectbox('Atividade a alterar',ids, key='admin_edit_select')
    row=tasks[tasks['ID da Tarefa']==chosen].iloc[0].to_dict()
    previous={col: row.get(col,'') for col in TASK_COLUMNS}
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
        description=st.text_input('Descrição',value=row['Descrição'])
        a,b,c=st.columns(3)
        with a: phase=choice('Fase',PHASES,row['Fase'])
        with b: priority=choice('Prioridade',PRIORITIES,row['Prioridade'])
        with c: status=choice('Status',STATUSES,row['Status'])
        has_deadline=st.checkbox('Tem previsão de conclusão?',value=bool(parse_date(row['Previsão de Conclusão'])))
        deadline=st.date_input('Previsão de conclusão',date_value(row['Previsão de Conclusão']),format='DD/MM/YYYY',disabled=not has_deadline)
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
              'Status':status,'Pendências/Observações':notes}
        _commit(update_task,chosen,previous,data)


def admin_diary():
    st.markdown('#### Novo relato do diário de bordo')
    st.caption('Informe o que você fez hoje em uma tarefa existente. Você pode também atualizar a fase e o status no mesmo lançamento.')
    if tasks.empty:
        st.warning('Cadastre ao menos uma atividade primeiro.')
        return
    ids=sorted(tasks['ID da Tarefa'].tolist())
    chosen=st.selectbox('ID vinculado',ids,key='admin_diary_select')
    t=tasks[tasks['ID da Tarefa']==chosen].iloc[0]
    st.caption(t['Descrição'])
    with st.form(f'add_diary_{chosen}',clear_on_submit=True):
        dt=st.date_input('Data da atualização',today,format='DD/MM/YYYY')
        a,b=st.columns(2)
        with a: phase=choice('Fase após esta atualização',PHASES,t['Fase'])
        with b: status=choice('Status após esta atualização',STATUSES,t['Status'])
        text=st.text_area('O que aconteceu? Decisões, ações, próximos passos e pendências',height=180)
        sync=st.checkbox('Atualizar também fase e status na atividade',value=True)
        submit=st.form_submit_button('Salvar no diário de bordo',type='primary',use_container_width=True)
    if submit:
        if not text.strip():
            st.error('Descreva o que aconteceu.')
        else:
            record={'Data da Atualização':format_date(dt),'ID da Tarefa':chosen,
                    'Fase Atualizada':phase,'Status Atualizado':status,
                    'Descrição do que aconteceu':text}
            _commit(add_diary_and_update,record,sync)


def admin_visit():
    st.markdown('#### Registrar visita contratual')
    if raw['visit_mode']=='legado':
        st.warning('O arquivo ainda não possui a aba Visitas_Contrato. Você pode simular a migração do histórico antes de registrar novas visitas.')
        st.markdown('**Criar controle de visitas e importar histórico**')
        st.caption('Importa uma visita por base/data de todas as tarefas existentes (até hoje). Os registros históricos importados serão identificados como **a validar**.')
        checked=st.checkbox('Entendo que a importação de visitas é estimada. Na demonstração, a criação não modifica a planilha original.' if demo_mode() else 'Tenho backup da planilha e autorizo criar a nova aba com o histórico deduplicado.')
        if st.button('Simular importação de visitas' if demo_mode() else 'Criar aba e migrar visitas',disabled=not checked,type='primary'):
            _commit(initialize_visits_from_tasks,raw['tasks'])
        return
    with st.form('add_visit_form',clear_on_submit=True):
        a,b,c=st.columns(3)
        dt=a.date_input('Data da visita',today,format='DD/MM/YYYY')
        base=b.selectbox('Base visitada',BASES[:-1])
        tipo=c.selectbox('Tipo de atendimento',['Presencial','Remoto'])
        related=st.selectbox('Atividade vinculada (opcional)',['Sem vínculo']+sorted(tasks['ID da Tarefa'].tolist()))
        summary=st.text_input('Resumo do objetivo da visita')
        observations=st.text_area('Observações e evidências',height=130)
        responsible=st.text_input('Responsável',value='Mothé Engenharia')
        submit=st.form_submit_button('Registrar visita',type='primary',use_container_width=True)
    if submit:
        if not summary.strip():
            st.error('O resumo é obrigatório.')
        elif dt > today and tipo == 'Presencial':
            st.error('Registre visitas futuras na agenda, mas contabilize somente as efetivamente realizadas.')
        else:
            record={'Data da Visita':format_date(dt),'Base':base,'Tipo':tipo,
                    'ID da Tarefa vinculada':'' if related=='Sem vínculo' else related,
                    'Resumo':summary,'Observações':observations,
                    'Responsável':responsible,'Origem':'Registro manual'}
            _commit(add_visit,record)


def admin_quality():
    st.markdown('#### Qualidade de dados e exportação')
    q=quality_issues(tasks)
    a,b,c=st.columns(3)
    a.metric('Diferenças fase/status',int(q['Aviso'].eq('Fase e status diferentes').sum()) if not q.empty else 0)
    b.metric('Sem previsão de conclusão',int(tasks['Previsão de Conclusão_dt'].isna().sum()))
    c.metric('Total de registros no diário',len(diary))
    if not q.empty:
        st.dataframe(q,hide_index=True,use_container_width=True)
    else:
        st.success('Não foram identificadas inconsistências pelas regras atuais.')
    st.caption('Nem todas as atividades precisam ter prazo; o alerta é informativo. Verifique também se há registros migrados de visitas a validar.')
    def csv_export(df):
        out=io.StringIO()
        copy=df.copy()
        for col in copy.columns:
            copy[col]=copy[col].map(lambda x: ("'"+x) if isinstance(x,str) and x.lstrip().startswith(('=','+','-','@')) else x)
        copy.to_csv(out,index=False)
        return ('\ufeff'+out.getvalue()).encode('utf-8')
    a,b=st.columns(2)
    a.download_button('Exportar atividades (CSV)',csv_export(tasks[TASK_COLUMNS]),
                      file_name='transforma_atividades.csv',mime='text/csv',use_container_width=True)
    b.download_button('Exportar diário (CSV)',csv_export(diary[DIARY_COLUMNS]),
                      file_name='transforma_diario.csv',mime='text/csv',use_container_width=True)


def admin_today():
    st.markdown('### 📝 Lançar o trabalho realizado no dia')
    st.caption('Escolha como deseja registrar o serviço. Uma atividade existente recebe um novo relato no Diário de Bordo; um serviço novo recebe um ID ACT automaticamente.')
    action = st.radio('O trabalho é de uma atividade já cadastrada?',
                      ['Sim — atualizar atividade existente', 'Não — cadastrar nova atividade'],
                      key='admin_today_kind')
    st.divider()
    if action.startswith('Sim'):
        admin_diary()
    else:
        admin_new_task()


def render_admin():
    header('Central de gestão',
           'Registre o trabalho do dia e acompanhe as demandas sem abrir a planilha.',
           'ÁREA EXCLUSIVA • ADMINISTRADOR')
    if raw.get('demo'):
        st.warning('**Modo de teste ativo:** os formulários estão liberados. As alterações são apenas nesta sessão, aparecem nos indicadores e podem ser exportadas; não modificam sua planilha Google.')
    elif not google_ready():
        st.warning('Edição indisponível até configurar a conta Google Sheets em Streamlit Secrets.')
        admin_quality()
        return
    admin_pages = ['📝 Lançar trabalho do dia', '＋ Nova atividade', '✎ Editar atividade',
                   '▤ Diário de bordo', '◉ Registrar visita', '✓ Conferência / Exportação']
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
elif page=='Diário de bordo':
    render_diary()
elif page=='Gestão administrativa' and st.session_state['role']=='admin':
    render_admin()

st.divider()
st.caption('Mothé Engenharia • Painel Transforma • Dados reais atualizados a cada 45 segundos; na demonstração, as informações são locais à sessão e não alteram o Google Sheets.')
