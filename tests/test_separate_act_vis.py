import io
import unittest
from unittest.mock import patch
import pandas as pd
from analytics import (
    TASK_COLUMNS, DIARY_COLUMNS, VISIT_COLUMNS, task_frame,
    activity_only_frame, delivery_frame, visit_frame,
    visits_from_register, contract_metrics,
)
from preview import parse_uploaded_workbook
from storage import create_task


class OnlyVisitsUseVisIds(unittest.TestCase):
    def test_legacy_visits_do_not_count_as_activities(self):
        rows=[
            {'ID da Tarefa':'ACT-001','Descrição':'Visita e reunião de alinhamento',
             'Tipo de Registro':'Atividade técnica','Status':'Resolvido'},
            {'ID da Tarefa':'ACT-002','Descrição':'Visita pré marcada',
             'Tipo de Registro':'Visita de rotina','Status':'Resolvido'},
            {'ID da Tarefa':'ACT-003','Descrição':'Conserto da bomba',
             'Tipo de Registro':'Atividade técnica','Status':'Resolvido'},
            {'ID da Tarefa':'ACT-004','Descrição':'Projeto da ETE',
             'Tipo de Registro':'Atividade técnica','Status':'Em Andamento'},
        ]
        data=task_frame(rows)
        self.assertEqual(activity_only_frame(data)['ID da Tarefa'].tolist(), ['ACT-003','ACT-004'])
        self.assertEqual(len(delivery_frame(data)),2)

    def test_create_task_rejects_visits_without_allocating_act(self):
        for values in [
          {'Descrição':'Visita pré marcada','Tipo de Registro':'Visita de rotina'},
          {'Descrição':'Visita de emergência para manutenção','Tipo de Registro':'Atividade técnica'},
          {'Descrição':'Acompanhamento em campo','Tipo de Registro':'Acompanhamento de campo'},
        ]:
            with self.subTest(values=values):
                with self.assertRaisesRegex(ValueError,'VIS'):
                    create_task(values)

    def test_normal_act_keeps_act_id(self):
        dataset={'tasks':[{'ID da Tarefa':'ACT-010'}]}
        with patch('storage.require_write'),patch('storage.demo_mode',return_value=True),\
             patch('storage._demo_data',return_value=dataset):
            result=create_task({'Descrição':'Projeto elétrico ETE','Tipo de Registro':'Atividade técnica'})
        self.assertEqual(result,'ACT-011')

    def test_canonical_tabs_win_over_archived_originals(self):
        activities=pd.DataFrame([
            {'ID da Tarefa':'ACT-012','Descrição':'Manutenção corretiva'},
        ]).reindex(columns=TASK_COLUMNS)
        archive=pd.DataFrame([
            {'ID da Tarefa':'ACT-002','Descrição':'Visita pré marcada'},
        ]).reindex(columns=TASK_COLUMNS)
        updates=pd.DataFrame(columns=DIARY_COLUMNS)
        visit=pd.DataFrame([{
            'ID da Visita':'VIS-0001','Data da Visita':'02/09/2026',
            'Base':'Macaé/RJ','Tipo':'Presencial','Resumo':'Visita de rotina',
        }]).reindex(columns=VISIT_COLUMNS)
        mem=io.BytesIO()
        with pd.ExcelWriter(mem,engine='openpyxl') as writer:
            activities.to_excel(writer,sheet_name='Atividades',index=False)
            archive.to_excel(writer,sheet_name='Arquivo_ACT_Visitas',index=False)
            updates.to_excel(writer,sheet_name='Atualizacoes',index=False)
            updates.to_excel(writer,sheet_name='Arquivo_Atualizacoes_VIS',index=False)
            visit.to_excel(writer,sheet_name='Visitas_Contrato',index=False)
        book=parse_uploaded_workbook(mem.getvalue())
        self.assertEqual(len(book['tasks']),1)
        self.assertEqual(book['tasks'][0]['ID da Tarefa'],'ACT-012')
        self.assertEqual(len(book['visits']),1)
        self.assertEqual(book['visits'][0]['ID da Visita'],'VIS-0001')


if __name__ == '__main__':
    unittest.main()
