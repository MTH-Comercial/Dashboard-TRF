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
DIARY_COLUMNS = [
    'Data da Atualização', 'ID da Tarefa', 'Fase Atualizada',
    'Status Atualizado', 'Descrição do que aconteceu',
]
VISIT_COLUMNS = [
    'ID da Visita', 'Data da Visita', 'Base', 'Tipo', 'ID da Tarefa vinculada',
    'Resumo', 'Observações', 'Responsável', 'Origem',
]
BASES = ['Macaé/RJ', 'Porto do Açu - São João da Barra/RJ',
         'Gradim - São Gonçalo/RJ', 'A definir']
STATUSES = [
    'Não Iniciado', 'Agendado', 'Em Andamento', 'Pausado',
    'Aguardando', 'Aguardando Terceiros', 'Aguardando Terceiro/Compras', 'Resolvido',
]
PHASES = [
    'Não Iniciado', 'Levantamento em Campo', 'Engenharia de Escritório',
    'Em Aprovação (Cliente)', 'Em Execução', 'Aguardando Terceiros', 'Concluído',
]
PRIORITIES = ['Rotina', 'Melhoria', 'Emergencial', 'Planejamento (Futuro)']
CATEGORIES = [
    'Consultoria, Estudos e Pareceres', 'Gestão e Treinamento',
    'Manutenção Corretiva/Emergencial', 'Projetos e Documentação',
    'Acompanhamento Técnico (Obras/Manutenção)',
]
CLOSED = {'Resolvido'}


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
        result[col] = result[col].map(lambda x: '' if x is None else str(x).strip())
    return result[columns].copy()


def task_frame(rows):
    df = frame(rows, TASK_COLUMNS)
    df = df[df['ID da Tarefa'].ne('')].copy()
    for name in ['Data de Início', 'Data da Visita', 'Previsão de Conclusão']:
        df[name + '_dt'] = df[name].map(parse_date)
    return df


def diary_frame(rows):
    df = frame(rows, DIARY_COLUMNS)
    df = df[df['ID da Tarefa'].ne('')].copy()
    df['Data da Atualização_dt'] = df['Data da Atualização'].map(parse_date)
    return df


def visit_frame(rows):
    df = frame(rows, VISIT_COLUMNS)
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
            data.append({'Data': dt, 'Base': base, 'Grupo': group, 'Origem': 'Tarefa'})
    return pd.DataFrame(data, columns=['Data', 'Base', 'Grupo', 'Origem'])


def visits_from_register(visits, start, end, today):
    """Só contam visitas presenciais registradas; uma por base e data."""
    seen = set()
    data = []
    for _, row in visits.iterrows():
        dt = row.get('Data da Visita_dt')
        base = row.get('Base', '')
        group = location_group(base)
        tipo = str(row.get('Tipo', '')).strip().casefold()
        if dt is None or group == 'Não classificada' or tipo != 'presencial':
            continue
        if not (start <= dt <= min(end, today)):
            continue
        key = (str(base).strip().casefold(), dt)
        if key not in seen:
            seen.add(key)
            data.append({'Data': dt, 'Base': base, 'Grupo': group, 'Origem': row.get('Origem','')})
    return pd.DataFrame(data, columns=['Data', 'Base', 'Grupo', 'Origem'])


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


def quality_issues(tasks):
    issues = []
    ids = tasks['ID da Tarefa'].tolist()
    for value in set(ids):
        if ids.count(value) > 1:
            issues.append((value, 'ID duplicado', 'A planilha exige IDs únicos.'))
    for _, row in tasks.iterrows():
        task_id = row['ID da Tarefa']
        if row['Status'] == 'Resolvido' and row['Fase'] != 'Concluído':
            issues.append((task_id, 'Fase e status diferentes', 'Resolvido com fase ainda aberta; confirmar se é intencional.'))
        elif row['Fase'] == 'Concluído' and row['Status'] != 'Resolvido':
            issues.append((task_id, 'Fase e status diferentes', 'Fase Concluído com status não resolvido.'))
        if row['Data de Início_dt'] is None:
            issues.append((task_id, 'Data de início inválida', 'Conferir data na planilha.'))
    return pd.DataFrame(issues, columns=['ID', 'Aviso', 'Ação sugerida'])


def new_task_id(ids):
    used = set(str(item) for item in ids)
    numbers = [int(m.group(1)) for item in used if (m := re.fullmatch(r'ACT-(\d+)', item))]
    candidate = (max(numbers, default=0) + 1)
    while f'ACT-{candidate:03d}' in used:
        candidate += 1
    return f'ACT-{candidate:03d}'


def pct(numerator, denominator):
    return 100 * numerator / denominator if denominator else 0
