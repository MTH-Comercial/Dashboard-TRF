"""Importação temporária e validada de planilhas XLSX para revisão no navegador.

Nenhum registro importado é enviado ao GitHub ou escrito no Google Sheets.
"""
from __future__ import annotations
from io import BytesIO
import math
import pandas as pd
from analytics import TASK_COLUMNS, TASK_EXTRA_COLUMNS, DIARY_COLUMNS, VISIT_COLUMNS, VISIT_EXTRA_COLUMNS, format_date

MAX_XLSX_SIZE = 8 * 1024 * 1024
DATE_FIELDS = {'Data de Início', 'Data da Visita', 'Previsão de Conclusão', 'Data da Atualização'}


def _select_tab(tabs: dict, required: list[str], *, optional: bool = False):
    matches = []
    for tab_name, sheet in tabs.items():
        if set(required).issubset({str(x).strip() for x in sheet.columns}):
            matches.append((tab_name, sheet))
    if not matches:
        if optional:
            return None, None
        raise ValueError(f'Não encontrei uma aba com os campos obrigatórios: {", ".join(required[:3])}...')
    if len(matches) != 1:
        raise ValueError('Mais de uma aba contém os mesmos campos necessários; confira o arquivo antes de carregar.')
    return matches[0]


def _cell(value, name: str):
    if value is None:
        return ''
    try:
        if pd.isna(value):
            return ''
    except (TypeError, ValueError):
        pass
    if name in DATE_FIELDS:
        return format_date(value)
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _records(sheet: pd.DataFrame, columns: list[str]):
    records = []
    for row in sheet[columns].itertuples(index=False, name=None):
        record = {field: _cell(value, field) for field, value in zip(columns, row)}
        if record[columns[0]]:
            records.append(record)
    return records


def parse_uploaded_workbook(file_bytes: bytes):
    """Carrega o XLSX em memória; exige cabeçalhos oficiais e IDs únicos."""
    if not file_bytes:
        raise ValueError('Arquivo vazio.')
    if len(file_bytes) > MAX_XLSX_SIZE:
        raise ValueError('O arquivo excede 8 MB; exporte apenas as abas do dashboard.')
    if not file_bytes.startswith(b'PK'):
        raise ValueError('O arquivo não parece ser um Excel (.xlsx).')
    try:
        tabs = pd.read_excel(BytesIO(file_bytes), sheet_name=None, dtype=object, engine='openpyxl')
    except Exception as exc:
        raise ValueError('Não foi possível ler o Excel. Baixe novamente em formato .xlsx.') from exc
    tasks_name, tasks_sheet = _select_tab(tabs, TASK_COLUMNS)
    diary_name, diary_sheet = _select_tab(tabs, DIARY_COLUMNS)
    visits_name, visits_sheet = _select_tab(tabs, VISIT_COLUMNS, optional=True)
    # A cópia histórica só tinha 12 campos; os complementares são opcionais.
    available = TASK_COLUMNS + [c for c in TASK_EXTRA_COLUMNS if c in tasks_sheet.columns]
    tasks = _records(tasks_sheet, available)
    diary = _records(diary_sheet, DIARY_COLUMNS)
    visit_fields = VISIT_COLUMNS + ([k for k in VISIT_EXTRA_COLUMNS if k in visits_sheet.columns] if visits_sheet is not None else [])
    visits = _records(visits_sheet, visit_fields) if visits_sheet is not None else []
    if not tasks:
        raise ValueError('A planilha não contém atividades com ID válido.')
    ids = [t['ID da Tarefa'] for t in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError('Existem IDs de atividades repetidos; corrija antes de carregar.')
    return {
        'tasks': tasks, 'diary': diary, 'visits': visits,
        'visit_mode': 'registro' if visits_name else 'legado',
        'demo': True,
        'source': f'Excel importado: {len(tasks)} atividades e {len(diary)} registros de diário',
        'tabs': {'activities': tasks_name, 'diary': diary_name, 'visits': visits_name},
    }
