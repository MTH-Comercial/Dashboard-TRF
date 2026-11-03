import io
import unittest
import pandas as pd
from preview import parse_uploaded_workbook
from analytics import TASK_COLUMNS, DIARY_COLUMNS


class SpreadsheetPreviewTest(unittest.TestCase):
    @staticmethod
    def sample():
        activities = pd.DataFrame([
            {'ID da Tarefa': 'ACT-001', 'Data de Início': pd.Timestamp('2026-09-02'),
             'Base': 'Macaé/RJ', 'Descrição': 'Reunião inicial', 'Status': 'Resolvido'},
            {'ID da Tarefa': 'ACT-002', 'Data de Início': pd.Timestamp('2026-09-03'),
             'Base': 'Macaé/RJ', 'Descrição': 'Projeto de iluminação', 'Status': 'Em Andamento'},
        ]).reindex(columns=TASK_COLUMNS)
        diary = pd.DataFrame([{'Data da Atualização': pd.Timestamp('2026-09-03'),
                               'ID da Tarefa': 'ACT-002',
                               'Descrição do que aconteceu': 'Primeiro levantamento'}]
                             ).reindex(columns=DIARY_COLUMNS)
        data = io.BytesIO()
        with pd.ExcelWriter(data, engine='openpyxl') as writer:
            activities.to_excel(writer, sheet_name='Base_de_Dados', index=False)
            diary.to_excel(writer, sheet_name='Diario_de_Bordo', index=False)
        return data.getvalue()

    def test_workbook_imports_without_leaking_to_repo(self):
        result = parse_uploaded_workbook(self.sample())
        self.assertEqual(len(result['tasks']), 2)
        self.assertEqual(len(result['diary']), 1)
        self.assertEqual(result['tasks'][0]['Data de Início'], '02/09/2026')
        self.assertEqual(result['diary'][0]['Data da Atualização'], '03/09/2026')
        self.assertEqual(result['visit_mode'], 'legado')

    def test_invalid_excel_rejected(self):
        with self.assertRaises(ValueError):
            parse_uploaded_workbook(b'not xlsx')

    def test_missing_diary_tab_rejected(self):
        data = io.BytesIO()
        with pd.ExcelWriter(data, engine='openpyxl') as writer:
            pd.DataFrame(columns=TASK_COLUMNS).to_excel(writer, sheet_name='tasks', index=False)
        with self.assertRaises(ValueError):
            parse_uploaded_workbook(data.getvalue())


if __name__ == '__main__':
    unittest.main()
