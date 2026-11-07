"""Regressões: prazo editável e novas linhas com estilo, filtro e datas consistentes."""
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from storage import _append_formatted_row, _sheet_value, _write_values


class SheetWriteTests(unittest.TestCase):
    def test_date_saved_iso_and_not_regional_serial(self):
        self.assertEqual(_sheet_value('Previsão de Conclusão','12/11/2026'),'2026-11-12')
        self.assertEqual(_sheet_value('Data de Início','05/11/2026'),'2026-11-05')
        self.assertEqual(_sheet_value('Data da Visita','2026-11-03'),'2026-11-03')

    def test_new_row_inherits_style_and_extends_filter(self):
        sheet = MagicMock()
        sheet.id = 1717245555
        sheet.append_row.return_value = {'updates': {'updatedRange': 'Atividades!A32:O32'}}
        sheet.spreadsheet.fetch_sheet_metadata.return_value = {
            'sheets': [{'properties': {'sheetId': 1717245555},
                        'basicFilter': {'range': {
                            'sheetId': 1717245555, 'startRowIndex': 0,
                            'endRowIndex': 31, 'startColumnIndex': 0, 'endColumnIndex': 15}}}]}
        fields=['ID da Tarefa','Data de Início','Previsão de Conclusão']
        _append_formatted_row(sheet, fields,
                              {'ID da Tarefa':'ACT-054','Data de Início':'05/11/2026',
                               'Previsão de Conclusão':'12/11/2026'})
        args, kwargs=sheet.append_row.call_args
        self.assertEqual(args[0], ['ACT-054','2026-11-05','2026-11-12'])
        self.assertEqual(kwargs['value_input_option'], 'RAW')
        reqs=sheet.spreadsheet.batch_update.call_args.args[0]['requests']
        self.assertEqual(reqs[0]['copyPaste']['pasteType'],'PASTE_FORMAT')
        self.assertEqual(reqs[0]['copyPaste']['destination']['startRowIndex'],31)
        self.assertEqual(reqs[1]['autoResizeDimensions']['dimensions']['endIndex'],32)
        self.assertEqual(reqs[2]['setBasicFilter']['filter']['range']['endRowIndex'],32)

    def test_same_deadline_two_formats_does_not_rewrite(self):
        sheet=MagicMock()
        sheet.row_values.return_value=['Previsão de Conclusão']
        self.assertEqual(_write_values(sheet, 32,
             {'Previsão de Conclusão':'2026-11-12'},
             {'Previsão de Conclusão':'12/11/2026'}, ['Previsão de Conclusão']),0)
        sheet.batch_update.assert_not_called()

    def test_edit_deadline_is_raw_iso(self):
        sheet=MagicMock()
        sheet.row_values.return_value=['Previsão de Conclusão']
        self.assertEqual(_write_values(sheet,32,{'Previsão de Conclusão':''},
             {'Previsão de Conclusão':'12/11/2026'},['Previsão de Conclusão']),1)
        self.assertEqual(sheet.batch_update.call_args.kwargs['value_input_option'], 'RAW')
        self.assertEqual(sheet.batch_update.call_args.args[0][0]['values'], [['2026-11-12']])

    def test_forms_do_not_disable_date_inside_form(self):
        source=Path(__file__).resolve().parents[1].joinpath('app.py').read_text()
        self.assertNotIn('disabled=not has_deadline',source)


if __name__=='__main__':
    unittest.main()
