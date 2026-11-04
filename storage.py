"""Leitura e escrita na planilha original via conta de serviço Google."""
from __future__ import annotations
import csv
import os
import io
from pathlib import Path
import gspread
import streamlit as st
from analytics import TASK_COLUMNS, TASK_EXTRA_COLUMNS, ALL_TASK_COLUMNS, DIARY_COLUMNS, VISIT_COLUMNS, ALL_VISIT_COLUMNS, VISIT_EXTRA_COLUMNS, visit_purpose, new_task_id, today_brazil, task_frame, visits_from_tasks
from security import safe_user_entry

DEFAULT_SHEET_ID = '1LgXQeTJ4FK1h8VLGRWijU3oGaE_FNg5gBTuB6XhEiKI'
TASKS_GID = 1562629984
DIARY_GID = 997870532
VISIT_TAB = 'Visitas_Contrato'
TASKS_TAB = 'Atividades'
DIARY_TAB = 'Atualizacoes'


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


def read_records(ws, columns, required=None):
    values = ws.get_all_values(value_render_option='FORMATTED_VALUE')
    if not values:
        return []
    headers = [str(h).strip() for h in values[0]]
    absent = [c for c in (required if required is not None else columns) if c not in headers]
    if absent:
        raise ValueError(f'A aba {ws.title} não possui as colunas: {", ".join(absent)}')
    output = []
    for row_num, line in enumerate(values[1:], start=2):
        if not any(str(v).strip() for v in line):
            continue
        full = line + [''] * max(0, len(headers) - len(line))
        obj = {col: full[headers.index(col)] if col in headers else '' for col in columns}
        obj['__sheet_row'] = row_num
        output.append(obj)
    return output


def load_demo():
    # Armazenamento exclusivo desta sessão Streamlit (NÃO compartilhado no cache global).
    if 'demo_dataset' not in st.session_state:
        folder = Path(__file__).parent / 'demo_data'
        def load(name):
            with (folder / name).open(encoding='utf-8-sig', newline='') as fh:
                return list(csv.DictReader(fh))
        st.session_state['demo_dataset'] = {
            'tasks': load('tasks.csv'), 'diary': load('diary.csv'),
            'visits': load('visits.csv'), 'visit_mode': 'registro', 'demo': True,
            'source': '4 registros fictícios (substituíveis pelo seu Excel)',
        }
    return st.session_state['demo_dataset']


def demo_replace_dataset(parsed):
    if not demo_mode() or st.session_state.get('role') != 'admin':
        raise PermissionError('A importação de demonstração exige perfil administrador.')
    st.session_state['demo_dataset'] = parsed


def _demo_data():
    if not demo_mode():
        raise PermissionError('Operação de demonstração indisponível no ambiente real.')
    if st.session_state.get('role') != 'admin':
        raise PermissionError('Apenas o administrador pode editar os dados da sessão.')
    return load_demo()


def get_tab(book, preferred_title, legacy_gid):
    """A nova base usa nomes estáveis; a base antiga permanece compatível."""
    try:
        return book.worksheet(preferred_title)
    except gspread.WorksheetNotFound:
        return book.get_worksheet_by_id(legacy_gid)


def load_live():
    book = connect()
    tasks = read_records(get_tab(book,TASKS_TAB,TASKS_GID), ALL_TASK_COLUMNS, required=TASK_COLUMNS)
    diary = read_records(get_tab(book,DIARY_TAB,DIARY_GID), DIARY_COLUMNS)
    try:
        visit_ws = book.worksheet(VISIT_TAB)
    except gspread.WorksheetNotFound:
        visit_ws = None
    visits = read_records(visit_ws, ALL_VISIT_COLUMNS, required=VISIT_COLUMNS) if visit_ws else []
    return {'tasks': tasks, 'diary': diary, 'visits': visits,
            'visit_mode': 'registro' if visit_ws is not None else 'legado', 'demo': False}


@st.cache_data(ttl=45, show_spinner=False)
def _load_live_cached():
    return load_live()


def load_all():
    # IMPORTANTE: não armazenar dados privados da sessão em cache de uso global.
    return load_demo() if demo_mode() else _load_live_cached()


def clear_data_cache():
    _load_live_cached.clear()


def require_write():
    if st.session_state.get('role') != 'admin':
        raise PermissionError('Apenas administradores podem alterar dados.')
    if not demo_mode() and not google_ready():
        raise PermissionError('Conta de serviço Google Sheets não configurada.')


def _sheet(gid):
    book=connect()
    if gid==TASKS_GID:
        return get_tab(book,TASKS_TAB,TASKS_GID)
    if gid==DIARY_GID:
        return get_tab(book,DIARY_TAB,DIARY_GID)
    return book.get_worksheet_by_id(gid)


def ensure_visit_headers(ws):
    headers=[str(x).strip() for x in ws.row_values(1)]
    missing=[c for c in VISIT_EXTRA_COLUMNS if c not in headers]
    if missing:
        ws.update(range_name=gspread.utils.rowcol_to_a1(1,len(headers)+1), values=[missing], value_input_option='RAW')
    return [str(x).strip() for x in ws.row_values(1)]


def _find_row(ws, task_id, columns=TASK_COLUMNS):
    recs = read_records(ws, columns)
    found = [r for r in recs if r[columns[0]] == task_id]
    if len(found) != 1:
        raise ValueError('ID não encontrado ou duplicado. Atualize a página.')
    return found[0]


def ensure_task_headers(ws):
    """Acrescenta campos na primeira linha SEM substituir as 12 colunas antigas."""
    headers = [str(x).strip() for x in ws.row_values(1)]
    missing = [c for c in TASK_EXTRA_COLUMNS if c not in headers]
    if missing:
        ws.update(range_name=f'{gspread.utils.rowcol_to_a1(1,len(headers)+1)}', values=[missing], value_input_option='RAW')
    return [str(x).strip() for x in ws.row_values(1)]


def _write_values(ws, row_num, old, new, columns):
    """Escreve somente células alteradas, sem regravar as demais colunas."""
    changes = []
    headers = [str(x).strip() for x in ws.row_values(1)]
    for col in columns:
        if col not in headers:
            continue
        index = headers.index(col) + 1
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
    if demo_mode():
        dataset = _demo_data()
        task_id = new_task_id([r['ID da Tarefa'] for r in dataset['tasks']])
        dataset['tasks'].append({c: safe_user_entry(task_id if c == 'ID da Tarefa' else values.get(c, '')) for c in ALL_TASK_COLUMNS})
        return task_id
    ws = _sheet(TASKS_GID)
    headers = ensure_task_headers(ws)
    recs = read_records(ws, ALL_TASK_COLUMNS, required=TASK_COLUMNS)
    task_id = new_task_id([r['ID da Tarefa'] for r in recs])
    data = dict(values, **{'ID da Tarefa': task_id})
    row = [safe_user_entry(data.get(c, '')) if c in ALL_TASK_COLUMNS else '' for c in headers]
    ws.append_row(row, value_input_option='USER_ENTERED')
    clear_data_cache()
    return task_id


def update_task(task_id, previous, values):
    require_write()
    if demo_mode():
        dataset = _demo_data()
        rows = [r for r in dataset['tasks'] if r['ID da Tarefa'] == task_id]
        if len(rows) != 1:
            raise ValueError('Atividade não encontrada ou duplicada.')
        old = rows[0]
        if any(str(old.get(c, '')).strip() != str(previous.get(c, '')).strip() for c in TASK_COLUMNS):
            raise ValueError('Os dados mudaram nesta sessão. Atualize antes de editar.')
        old.update({c: safe_user_entry(values.get(c, '')) for c in ALL_TASK_COLUMNS})
        return 1
    ws = _sheet(TASKS_GID)
    ensure_task_headers(ws)
    live = _find_row(ws, task_id, ALL_TASK_COLUMNS)
    if any(str(live[c]).strip() != str(previous.get(c, '')).strip() for c in TASK_COLUMNS):
        raise ValueError('A atividade mudou na planilha desde sua abertura. Recarregue antes de editar.')
    changes = _write_values(ws, live['__sheet_row'], live, values, ALL_TASK_COLUMNS)
    clear_data_cache()
    return changes


def add_diary_and_update(row_values, update_current=False, waiting_reason=None):
    require_write()
    task_id = str(row_values['ID da Tarefa'])
    if demo_mode():
        dataset = _demo_data()
        matched = [r for r in dataset['tasks'] if r['ID da Tarefa'] == task_id]
        if len(matched) != 1:
            raise ValueError('Atividade inexistente ou duplicada.')
        record = {c: safe_user_entry(row_values.get(c, '')) for c in DIARY_COLUMNS}
        if any(all(x.get(c, '') == record[c] for c in DIARY_COLUMNS) for x in dataset['diary']):
            raise ValueError('Relato idêntico já registrado nesta sessão.')
        dataset['diary'].append(record)
        if update_current:
            matched[0]['Fase'] = record['Fase Atualizada']
            matched[0]['Status'] = record['Status Atualizado']
            if waiting_reason is not None:
                matched[0]['Motivo de Espera'] = safe_user_entry(waiting_reason)
        return

    ws_tasks = _sheet(TASKS_GID)
    if update_current and waiting_reason is not None:
        ensure_task_headers(ws_tasks)
    live_task = _find_row(ws_tasks, task_id, ALL_TASK_COLUMNS if waiting_reason is not None and update_current else TASK_COLUMNS)
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
        if waiting_reason is not None:
            new['Motivo de Espera'] = safe_user_entry(waiting_reason)
        _write_values(ws_tasks, live_task['__sheet_row'], live_task, new, ALL_TASK_COLUMNS if waiting_reason is not None else TASK_COLUMNS)
    clear_data_cache()


def initialize_visits_from_tasks(tasks):
    """Cria uma aba, importando só pares únicos de data + base. Não altera abas existentes."""
    require_write()
    if demo_mode():
        dataset = _demo_data()
        if dataset['visit_mode'] == 'registro':
            raise ValueError('O registro de visitas já foi criado na demonstração.')
        from datetime import date
        imported = visits_from_tasks(task_frame(tasks), date(1900, 1, 1), date(2100, 1, 1), today_brazil())
        dataset['visits'] = [{
            'ID da Visita': f'VIS-{i:04d}', 'Data da Visita': r['Data'].strftime('%d/%m/%Y'),
            'Base': r['Base'], 'Tipo': 'Presencial', 'ID da Tarefa vinculada': '',
            'Resumo': 'Visita migrada das atividades (conferir)',
            'Observações': 'Migração temporária: validar ocorrência presencial.',
            'Responsável': '', 'Origem': 'Migração de tarefas (a validar)',
            'Finalidade': r.get('Finalidade','Outro'), 'Validação':'A validar',
        } for i, (_, r) in enumerate(imported.sort_values('Data').iterrows(), start=1)]
        dataset['visit_mode'] = 'registro'
        return len(dataset['visits'])
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
    ws = book.add_worksheet(title=VISIT_TAB, rows=max(1000, len(imported)+30), cols=len(ALL_VISIT_COLUMNS))
    ws.append_row(ALL_VISIT_COLUMNS, value_input_option='RAW')
    rows = []
    for idx, (_, r) in enumerate(imported.sort_values('Data').iterrows(), start=1):
        rows.append([
            f'VIS-{idx:04d}', r['Data'].strftime('%d/%m/%Y'), r['Base'], 'Presencial',
            '', 'Visita migrada da planilha de atividades',
            'Registro histórico inferido da data da visita de uma atividade. Validar antes da auditoria.',
            '', 'Migração de tarefas (a validar)',r.get('Finalidade','Outro'),'A validar',
        ])
    if rows:
        ws.append_rows(rows, value_input_option='USER_ENTERED', table_range='A:K')
    ws.freeze(rows=1)
    clear_data_cache()
    return len(rows)


def add_visit(data):
    require_write()
    if demo_mode():
        dataset = _demo_data()
        if dataset['visit_mode'] != 'registro':
            raise ValueError('Primeiro inicialize o registro de visitas.')
        records = dataset['visits']
        if data['Tipo'] == 'Presencial' and any(
            r['Data da Visita'] == data['Data da Visita']
            and r['Base'] == data['Base'] and r['Tipo'] == 'Presencial' for r in records
        ):
            raise ValueError('Visita presencial já existe nessa base e data.')
        ids = [int(r['ID da Visita'].split('-')[-1]) for r in records
               if r['ID da Visita'].startswith('VIS-') and r['ID da Visita'].split('-')[-1].isdigit()]
        visit_id = f'VIS-{max(ids, default=0)+1:04d}'
        records.append({c: safe_user_entry(visit_id if c == 'ID da Visita' else data.get(c, '')) for c in ALL_VISIT_COLUMNS})
        return visit_id
    book = connect()
    try:
        ws = book.worksheet(VISIT_TAB)
    except gspread.WorksheetNotFound:
        raise ValueError('Inicialize a aba Visitas_Contrato primeiro.')
    ensure_visit_headers(ws)
    records = read_records(ws, ALL_VISIT_COLUMNS, required=VISIT_COLUMNS)
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
    headers=ensure_visit_headers(ws)
    row=[safe_user_entry(data.get(col,'')) for col in headers]
    ws.append_row(row, value_input_option='USER_ENTERED', table_range='A:K')
    clear_data_cache()
    return visit_id

