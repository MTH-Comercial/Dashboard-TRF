"""Leitura e escrita na planilha original via conta de serviço Google."""
from __future__ import annotations
import csv
import os
import io
from pathlib import Path
import gspread
import streamlit as st
from analytics import TASK_COLUMNS, DIARY_COLUMNS, VISIT_COLUMNS, new_task_id, today_brazil
from security import safe_user_entry

DEFAULT_SHEET_ID = '1LgXQeTJ4FK1h8VLGRWijU3oGaE_FNg5gBTuB6XhEiKI'
TASKS_GID = 1562629984
DIARY_GID = 997870532
VISIT_TAB = 'Visitas_Contrato'


def secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except (FileNotFoundError, RuntimeError):
        return default


def demo_mode():
    return os.getenv('TRANSFORMA_DEMO') == '1' or bool(secret('DEMO_MODE', False))


def google_ready():
    return bool(secret('gcp_service_account'))


def connect():
    creds = secret('gcp_service_account')
    if not creds:
        raise RuntimeError('Conexão Google Sheets não configurada nas Secrets.')
    gc = gspread.service_account_from_dict(dict(creds))
    return gc.open_by_key(str(secret('SHEET_ID', DEFAULT_SHEET_ID)))


def read_records(ws, columns):
    values = ws.get_all_values(value_render_option='FORMATTED_VALUE')
    if not values:
        return []
    headers = [str(h).strip() for h in values[0]]
    absent = [c for c in columns if c not in headers]
    if absent:
        raise ValueError(f'A aba {ws.title} não possui as colunas: {", ".join(absent)}')
    output = []
    for row_num, line in enumerate(values[1:], start=2):
        if not any(str(v).strip() for v in line):
            continue
        full = line + [''] * max(0, len(headers) - len(line))
        obj = {col: full[headers.index(col)] for col in columns}
        obj['__sheet_row'] = row_num
        output.append(obj)
    return output


def load_demo():
    folder = Path(__file__).parent / 'demo_data'
    def load(name):
        with (folder / name).open(encoding='utf-8-sig', newline='') as fh:
            return list(csv.DictReader(fh))
    return {'tasks': load('tasks.csv'), 'diary': load('diary.csv'),
            'visits': load('visits.csv'), 'visit_mode': 'registro', 'demo': True}


def load_live():
    book = connect()
    tasks = read_records(book.get_worksheet_by_id(TASKS_GID), TASK_COLUMNS)
    diary = read_records(book.get_worksheet_by_id(DIARY_GID), DIARY_COLUMNS)
    try:
        visit_ws = book.worksheet(VISIT_TAB)
    except gspread.WorksheetNotFound:
        visit_ws = None
    visits = read_records(visit_ws, VISIT_COLUMNS) if visit_ws else []
    return {'tasks': tasks, 'diary': diary, 'visits': visits,
            'visit_mode': 'registro' if visit_ws is not None else 'legado', 'demo': False}


@st.cache_data(ttl=45, show_spinner=False)
def load_all():
    return load_demo() if demo_mode() else load_live()


def require_write():
    if demo_mode() or not google_ready():
        raise PermissionError('Escrita indisponível em modo demonstração ou sem conta Google.')
    if st.session_state.get('role') != 'admin':
        raise PermissionError('Apenas administradores podem alterar dados.')


def _sheet(gid):
    return connect().get_worksheet_by_id(gid)


def _find_row(ws, task_id, columns=TASK_COLUMNS):
    recs = read_records(ws, columns)
    found = [r for r in recs if r[columns[0]] == task_id]
    if len(found) != 1:
        raise ValueError('ID não encontrado ou duplicado. Atualize a página.')
    return found[0]


def _write_values(ws, row_num, old, new, columns):
    """Escreve somente células alteradas, sem regravar as demais colunas."""
    changes = []
    for index, col in enumerate(columns, start=1):
        before = str(old.get(col, '')).strip()
        after = str(new.get(col, '')).strip()
        if before != after:
            address = f'{gspread.utils.rowcol_to_a1(row_num, index)}'
            changes.append({'range': address, 'values': [[safe_user_entry(after)]]})
    if changes:
        ws.batch_update(changes, value_input_option='USER_ENTERED')
    return len(changes)


def create_task(values):
    require_write()
    ws = _sheet(TASKS_GID)
    recs = read_records(ws, TASK_COLUMNS)
    task_id = new_task_id([r['ID da Tarefa'] for r in recs])
    data = dict(values, **{'ID da Tarefa': task_id})
    row = [safe_user_entry(data.get(c, '')) for c in TASK_COLUMNS]
    ws.append_row(row, value_input_option='USER_ENTERED', table_range='A:L')
    load_all.clear()
    return task_id


def update_task(task_id, previous, values):
    require_write()
    ws = _sheet(TASKS_GID)
    live = _find_row(ws, task_id)
    if any(str(live[c]).strip() != str(previous.get(c, '')).strip() for c in TASK_COLUMNS):
        raise ValueError('A atividade mudou na planilha desde sua abertura. Recarregue antes de editar.')
    changes = _write_values(ws, live['__sheet_row'], live, values, TASK_COLUMNS)
    load_all.clear()
    return changes


def add_diary_and_update(row_values, update_current=False):
    require_write()
    task_id = str(row_values['ID da Tarefa'])
    ws_tasks = _sheet(TASKS_GID)
    live_task = _find_row(ws_tasks, task_id)
    ws_diary = _sheet(DIARY_GID)
    existing = read_records(ws_diary, DIARY_COLUMNS)
    for r in existing:
        if all(str(r.get(k,'')).strip() == str(row_values.get(k,'')).strip() for k in DIARY_COLUMNS):
            raise ValueError('Esse relato idêntico já existe no diário de bordo.')
    ws_diary.append_row(
        [safe_user_entry(row_values.get(c, '')) for c in DIARY_COLUMNS],
        value_input_option='USER_ENTERED', table_range='A:E',
    )
    if update_current:
        new = dict(live_task)
        new['Fase'] = row_values['Fase Atualizada']
        new['Status'] = row_values['Status Atualizado']
        _write_values(ws_tasks, live_task['__sheet_row'], live_task, new, TASK_COLUMNS)
    load_all.clear()


def initialize_visits_from_tasks(tasks):
    """Cria uma aba, importando só pares únicos de data + base. Não altera abas existentes."""
    require_write()
    book = connect()
    try:
        book.worksheet(VISIT_TAB)
        raise ValueError('A aba de visitas já existe. Nada foi migrado.')
    except gspread.WorksheetNotFound:
        pass
    from analytics import task_frame, visits_from_tasks
    from datetime import date
    df_tasks = task_frame(tasks)
    imported = visits_from_tasks(df_tasks, date(1900,1,1), date(2100,1,1), today_brazil())
    ws = book.add_worksheet(title=VISIT_TAB, rows=max(1000, len(imported)+30), cols=len(VISIT_COLUMNS))
    ws.append_row(VISIT_COLUMNS, value_input_option='RAW')
    rows = []
    for idx, (_, r) in enumerate(imported.sort_values('Data').iterrows(), start=1):
        rows.append([
            f'VIS-{idx:04d}', r['Data'].strftime('%d/%m/%Y'), r['Base'], 'Presencial',
            '', 'Visita migrada da planilha de atividades',
            'Registro histórico inferido da data da visita de uma atividade. Validar antes da auditoria.',
            '', 'Migração de tarefas (a validar)',
        ])
    if rows:
        ws.append_rows(rows, value_input_option='USER_ENTERED', table_range='A:I')
    ws.freeze(rows=1)
    load_all.clear()
    return len(rows)


def add_visit(data):
    require_write()
    book = connect()
    try:
        ws = book.worksheet(VISIT_TAB)
    except gspread.WorksheetNotFound:
        raise ValueError('Inicialize a aba Visitas_Contrato primeiro.')
    records = read_records(ws, VISIT_COLUMNS)
    values = list(records)
    if any(
        r['Data da Visita'] == data['Data da Visita'] and
        r['Base'] == data['Base'] and r['Tipo'] == 'Presencial' and data['Tipo'] == 'Presencial'
        for r in values
    ):
        raise ValueError('Já existe uma visita presencial nessa base e data. Abra a planilha para conferir.')
    ids = [int(r['ID da Visita'].split('-')[-1]) for r in values
           if r['ID da Visita'].startswith('VIS-') and r['ID da Visita'].split('-')[-1].isdigit()]
    visit_id = f'VIS-{max(ids, default=0)+1:04d}'
    data = dict(data, **{'ID da Visita': visit_id})
    row = [safe_user_entry(data.get(col, '')) for col in VISIT_COLUMNS]
    ws.append_row(row, value_input_option='USER_ENTERED', table_range='A:I')
    load_all.clear()
    return visit_id
