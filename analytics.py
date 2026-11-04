"""Regras de negócio isoladas da interface e do Google Sheets."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import re
import pandas as pd

TASK_COLUMNS = [
    'ID da Tarefa', 'Data de Início', 'Data da Visita', 'Base', 'Subárea',
    'Categoria', 'Descrição', 'Fase', 'Prioridade', 'Previsão de Conclusão',
    'Status', 'Pendências/Observações',
]
# Os três campos complementares são opcionais para as planilhas antigas.
# Permanecem após as 12 colunas originais; nunca são usados para alterar registros históricos automaticamente.
TASK_EXTRA_COLUMNS = ['Tipo de Registro', 'Condição do Prazo', 'Motivo de Espera']
ALL_TASK_COLUMNS = TASK_COLUMNS + TASK_EXTRA_COLUMNS
KIND_OPTIONS = [
    'Atividade técnica', 'Visita de rotina', 'Reunião/alinhamento',
    'Acompanhamento de campo', 'Demanda no radar',
]
# ACT nunca representa uma visita: toda presença contratual recebe VIS.
ACT_KIND_OPTIONS = ['Atividade técnica', 'Reunião/alinhamento', 'Demanda no radar']
VISIT_TASK_KINDS = {'Visita de rotina', 'Acompanhamento de campo'}
WAITING_STATUSES = {
    'Aguardando', 'Aguardando Cliente', 'Aguardando Aprovação',
    'Aguardando Terceiros', 'Aguardando Terceiro/Compras',
    'Aguardando Materiais', 'Aguardando Material/Compras', 'Pausado', 'Bloqueado',
}
DEADLINE_KINDS = [
    'Sem prazo definido', 'Estimativa interna', 'Compromisso confirmado',
    'Dependente de terceiros', 'Histórico sem classificação',
]

DIARY_COLUMNS = [
    'Data da Atualização', 'ID da Tarefa', 'Fase Atualizada',
    'Status Atualizado', 'Descrição do que aconteceu',
]
VISIT_COLUMNS = [
    'ID da Visita', 'Data da Visita', 'Base', 'Tipo', 'ID da Tarefa vinculada',
    'Resumo', 'Observações', 'Responsável', 'Origem',
]
VISIT_EXTRA_COLUMNS = ['Finalidade', 'Validação']
ALL_VISIT_COLUMNS = VISIT_COLUMNS + VISIT_EXTRA_COLUMNS
VISIT_PURPOSES = ['Rotina', 'Atendimento emergencial', 'Acompanhamento técnico', 'Reunião/alinhamento', 'Levantamento/projeto', 'Outro']
BASES = ['Macaé/RJ', 'Porto do Açu - São João da Barra/RJ',
         'Gradim - São Gonçalo/RJ', 'A definir']
STATUSES = [
    'Não Iniciado', 'Agendado', 'Em Andamento', 'Pausado',
    'Aguardando', 'Aguardando Cliente', 'Aguardando Aprovação', 'Aguardando Materiais',
    'Aguardando Terceiros', 'Aguardando Terceiro/Compras', 'Em Validação', 'Bloqueado', 'Resolvido', 'Realizado', 'Concluído',
]
PHASES = [
    'Não Iniciado', 'Levantamento em Campo', 'Engenharia de Escritório',
    'Em Aprovação (Cliente)', 'Em Execução', 'Em Testes/Validação', 'Aguardando Terceiros', 'Concluído',
]
PRIORITIES = ['Rotina', 'Melhoria', 'Baixa', 'Normal', 'Alta', 'Emergencial', 'Planejamento (Futuro)']
CATEGORIES = [
    'Consultoria, Estudos e Pareceres', 'Gestão e Treinamento',
    'Manutenção Corretiva/Emergencial', 'Projetos e Documentação',
    'Acompanhamento Técnico (Obras/Manutenção)',
]
CLOSED = {'Resolvido', 'Realizado', 'Concluído', 'Feito', 'Realizada'}


def today_brazil():
    """Data de referência do atendimento, independente do fuso do servidor Cloud."""
    return datetime.now(ZoneInfo('America/Sao_Paulo')).date()


def parse_date(value):
    """Aceita string BR, ISO, Excel serial e timestamps; retorna date|None."""
    if value is None:
        return None
    if not isinstance(value, (list, dict)) and pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        try:
            return (date(1899, 12, 30) + timedelta(days=int(value)))
        except (ValueError, OverflowError):
            return None
    raw = str(value).strip()
    if not raw or raw.lower() in {'nan', 'nat', 'none'}:
        return None
    # Também aceita números seriais que tenham chegado como strings do Excel.
    if re.fullmatch(r'\d{5}(?:\.0+)?', raw):
        n = int(float(raw))
        if 30000 <= n <= 70000:
            return date(1899, 12, 30) + timedelta(days=n)
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y %H:%M:%S'):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def format_date(value):
    dt = parse_date(value)
    return dt.strftime('%d/%m/%Y') if dt else ''


def frame(rows, columns):
    """Normaliza os cabeçalhos originais da planilha sem alterar suas colunas."""
    result = pd.DataFrame(rows)
    for col in columns:
        if col not in result.columns:
            result[col] = ''
        result[col] = result[col].map(lambda x: '' if x is None or (not isinstance(x,(list,dict)) and pd.isna(x)) else str(x).strip())
    return result[columns].copy()


def infer_record_kind(description, priority='', status=''):
    """Inferência CONSERVADORA: apenas visitas pré-marcadas e reuniões explícitas."""
    text = re.sub(r'\s+', ' ', str(description).casefold().strip())
    if re.search(r'visita\s+pr[eé][\s-]*marcada|visita\s+de\s+rotina', text):
        return 'Visita de rotina'
    if re.match(r'^(reuni[aã]o|alinhamento\b|visita\s+e\s+reuni[aã]o)', text):
        return 'Reunião/alinhamento'
    if re.match(r'^(visita\s+de\s+emerg[eê]ncia\s+para\s+acompanhamento|visita\s+de\s+emergencia\s+para\s+acompanhamento|visita$)', text):
        return 'Acompanhamento de campo'
    if priority == 'Planejamento (Futuro)' and status not in CLOSED:
        return 'Demanda no radar'
    return 'Atividade técnica'


def effective_closed(kind, status):
    return status in CLOSED


def display_status(kind, status):
    """Rótulos mais naturais para visitas e reuniões sem alterar o histórico."""
    if status == 'Resolvido' and kind in {'Visita de rotina','Acompanhamento de campo'}:
        return 'Realizada'
    if status == 'Resolvido' and kind == 'Reunião/alinhamento':
        return 'Realizada'
    return status


def visit_purpose(row):
    """Sugestão de finalidade por registro; não transforma demanda em visita."""
    kind=str(row.get('Tipo de Registro',''))
    description=str(row.get('Descrição','')).lower()
    priority=str(row.get('Prioridade',''))
    if 'reunião' in description or 'alinhamento' in description and kind=='Reunião/alinhamento': return 'Reunião/alinhamento'
    if kind=='Visita de rotina': return 'Rotina'
    if priority=='Emergencial': return 'Atendimento emergencial'
    if kind=='Acompanhamento de campo': return 'Acompanhamento técnico'
    if 'levantamento' in description or 'projeto' in description: return 'Levantamento/projeto'
    return 'Outro'


def task_frame(rows):
    df = frame(rows, ALL_TASK_COLUMNS)
    df = df[df['ID da Tarefa'].ne('')].copy()
    df['Tipo inferido'] = df['Tipo de Registro'].eq('')
    for i, r in df[df['Tipo inferido']].iterrows():
        df.loc[i, 'Tipo de Registro'] = infer_record_kind(r['Descrição'], r['Prioridade'], r['Status'])
    df['Condição do Prazo'] = df.apply(
        lambda r: r['Condição do Prazo'] or ('Histórico sem classificação' if parse_date(r['Previsão de Conclusão']) else 'Sem prazo definido'), axis=1)

    for name in ['Data de Início', 'Data da Visita', 'Previsão de Conclusão']:
        df[name + '_dt'] = df[name].map(parse_date)
    return df


def diary_frame(rows):
    df = frame(rows, DIARY_COLUMNS)
    df = df[df['ID da Tarefa'].ne('')].copy()
    df['Data da Atualização_dt'] = df['Data da Atualização'].map(parse_date)
    return df


def visit_frame(rows):
    df = frame(rows, ALL_VISIT_COLUMNS)
    df = df[df['Data da Visita'].ne('')].copy()
    df['Data da Visita_dt'] = df['Data da Visita'].map(parse_date)
    return df


def location_group(base):
    if 'Macaé' in str(base):
        return 'Macaé'
    if 'Açu' in str(base) or 'Gradim' in str(base):
        return 'Gradim/Açu'
    return 'Não classificada'


def contract_window(start, today=None):
    """Ciclo de 12 meses com fechamento no dia anterior ao aniversário."""
    s = parse_date(start)
    if s is None:
        raise ValueError('Configure CONTRACT_START como YYYY-MM-DD.')
    try:
        end = s.replace(year=s.year + 1) - timedelta(days=1)
    except ValueError:
        end = s.replace(year=s.year + 1, day=28) - timedelta(days=1)
    current = today or today_brazil()
    while current > end:
        s = end + timedelta(days=1)
        try:
            end = s.replace(year=s.year + 1) - timedelta(days=1)
        except ValueError:
            end = s.replace(year=s.year + 1, day=28) - timedelta(days=1)
    return s, end


def visits_from_tasks(tasks, start, end, today):
    """Compatibilidade: no máximo 1 visita por unidade e dia; somente datas passadas."""
    seen = set()
    data = []
    for _, row in tasks.iterrows():
        dt = row.get('Data da Visita_dt')
        base = row.get('Base', '')
        group = location_group(base)
        if dt is None or group == 'Não classificada' or not (start <= dt <= min(end, today)):
            continue
        key = (str(base).strip().casefold(), dt)
        if key not in seen:
            seen.add(key)
            data.append({'Data': dt, 'Base': base, 'Grupo': group, 'Origem': 'Estimativa a partir da atividade', 'Finalidade': visit_purpose(row)})
    return pd.DataFrame(data, columns=['Data', 'Base', 'Grupo', 'Origem', 'Finalidade'])


def visits_from_register(visits, start, end, today):
    """Só contam visitas presenciais registradas; uma por base e data."""
    seen = set()
    data = []
    for _, row in visits.iterrows():
        dt = row.get('Data da Visita_dt')
        base = row.get('Base', '')
        group = location_group(base)
        tipo = str(row.get('Tipo', '')).strip().casefold()
        if str(row.get('Validação','')).strip().casefold() == 'descartada':
            continue
        if dt is None or group == 'Não classificada' or tipo != 'presencial':
            continue
        if not (start <= dt <= min(end, today)):
            continue
        key = (str(base).strip().casefold(), dt)
        if key not in seen:
            seen.add(key)
            data.append({'ID da Visita': row.get('ID da Visita',''), 'Data': dt, 'Base': base, 'Grupo': group, 'Origem': row.get('Origem',''), 'Finalidade': row.get('Finalidade','Não informada') or 'Não informada'})
    return pd.DataFrame(data, columns=['ID da Visita', 'Data', 'Base', 'Grupo', 'Origem', 'Finalidade'])


def contract_metrics(visits_df):
    counts = visits_df['Grupo'].value_counts().to_dict() if not visits_df.empty else {}
    macae = counts.get('Macaé', 0)
    inter = counts.get('Gradim/Açu', 0)
    return {'macae': macae, 'inter': inter, 'total': macae + inter,
            'goal_macae': 104, 'goal_inter': 12,
            'pct_macae': macae / 104, 'pct_inter': inter / 12}


def task_metrics(tasks, today=None):
    current = today or today_brazil()
    statuses = tasks['Status'].value_counts().to_dict()
    n = len(tasks)
    resolved = statuses.get('Resolvido', 0)
    overdue = tasks[
        tasks['Previsão de Conclusão_dt'].map(lambda d: d is not None and d < current)
        & ~tasks['Status'].isin(CLOSED)
    ]
    return {
        'total': n, 'resolved': resolved, 'resolution_rate': resolved / n if n else 0,
        'ongoing': statuses.get('Em Andamento', 0),
        'waiting': sum(v for k, v in statuses.items() if k in {
            'Pausado', 'Aguardando', 'Aguardando Terceiros', 'Aguardando Terceiro/Compras'}),
        'not_started': sum(v for k,v in statuses.items() if k in {'Não Iniciado','Agendado'}),
        'emergencies': int(tasks['Prioridade'].eq('Emergencial').sum()),
        'overdue': len(overdue),
        'overdue_tasks': overdue,
    }


def is_delivery(row):
    return row.get('Tipo de Registro', '') == 'Atividade técnica'


def is_visit_record(row):
    """Visitas legadas, inclusive registros antigos tipados como 'Atividade técnica'."""
    kind = str(row.get('Tipo de Registro', '')).strip()
    description = str(row.get('Descrição', '')).strip().casefold()
    return kind in VISIT_TASK_KINDS or description.startswith('visita')


def activity_only_frame(tasks):
    """ACT só inclui projetos, serviços, reuniões e radar; visitas vão para VIS."""
    if tasks.empty:
        return tasks.copy()
    return tasks[~tasks.apply(is_visit_record, axis=1)].copy()


def delivery_frame(tasks):
    """Somente entregas de engenharia contam como atividades técnicas."""
    actual = activity_only_frame(tasks)
    return actual[actual['Tipo de Registro'].eq('Atividade técnica')].copy()


def is_radar(row):
    return (row.get('Status', '') not in CLOSED
            and row.get('Tipo de Registro', '') == 'Demanda no radar')


def delivery_overview(tasks, today=None):
    current = today or today_brazil()
    deliveries = delivery_frame(tasks)
    open_ = deliveries[~deliveries['Status'].isin(CLOSED)].copy()
    waiting = open_[open_['Status'].isin(WAITING_STATUSES)]
    radar = tasks[tasks.apply(is_radar, axis=1)]
    commitments = open_[open_['Condição do Prazo'].eq('Compromisso confirmado')]
    overdue_commitments = commitments[commitments['Previsão de Conclusão_dt'].map(
        lambda d: d is not None and d < current)]
    return {
        'deliveries': len(deliveries),
        'done': int(deliveries['Status'].isin(CLOSED).sum()),
        'active': int(open_['Status'].eq('Em Andamento').sum()),
        'waiting': len(waiting),
        'radar': len(radar),
        'routine_visits': int(tasks['Tipo de Registro'].eq('Visita de rotina').sum()),
        'meetings': int(tasks['Tipo de Registro'].eq('Reunião/alinhamento').sum()),
        'field_followups': int(tasks['Tipo de Registro'].eq('Acompanhamento de campo').sum()),
        'emergencies': int(deliveries['Prioridade'].eq('Emergencial').sum()),
        'late_commitments': len(overdue_commitments),
        'unclassified_kinds': int(tasks['Tipo inferido'].sum()),
    }


def quality_issues(tasks):
    """Somente problemas reais de cadastro, nunca transições históricas de fase/status."""
    issues=[]
    ids=tasks['ID da Tarefa'].tolist()
    for value in sorted(set(ids)):
        if ids.count(value)>1:
            issues.append((value,'ID duplicado','O ID deve ser único para o histórico e a edição.'))
    for _,row in tasks.iterrows():
        task_id=row['ID da Tarefa']
        if not row['Descrição'].strip():
            issues.append((task_id,'Descrição ausente','Identifique o serviço ou atendimento.'))
        # Demanda no radar sem data é intencional e permitida.
        if row['Data de Início'] and row['Data de Início_dt'] is None:
            issues.append((task_id,'Data inválida','Confira a data de início.'))
    return pd.DataFrame(issues,columns=['ID','Aviso','Ação sugerida'])


def sort_tasks_for_table(data):
    """Ordenação segura para tabelas vazias ou sem coluna auxiliar de data."""
    if data is None or data.empty:
        return pd.DataFrame() if data is None else data.copy()
    result = data.copy()
    if 'Data de Início_dt' in result.columns:
        result['_ordem_'] = pd.to_datetime(result['Data de Início_dt'], errors='coerce')
    elif 'Data de Início' in result.columns:
        result['_ordem_'] = pd.to_datetime(result['Data de Início'].map(parse_date), errors='coerce')
    else:
        result['_ordem_'] = pd.NaT
    return result.sort_values('_ordem_', ascending=False, na_position='last').drop(columns=['_ordem_'])


def new_task_id(ids):
    used = set(str(item) for item in ids)
    numbers = [int(m.group(1)) for item in used if (m := re.fullmatch(r'ACT-(\d+)', item))]
    candidate = (max(numbers, default=0) + 1)
    while f'ACT-{candidate:03d}' in used:
        candidate += 1
    return f'ACT-{candidate:03d}'


def pct(numerator, denominator):
    return 100 * numerator / denominator if denominator else 0

