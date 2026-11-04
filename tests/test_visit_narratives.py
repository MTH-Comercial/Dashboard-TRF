"""Regressões: histórico narrativo das visitas contratuais."""
import unittest
from datetime import date
from unittest.mock import patch
from analytics import task_frame
from storage import visit_source_for_day, update_visit

class VisitNarrativeTest(unittest.TestCase):
    def test_prefers_daily_routine_note_on_same_date(self):
        data = task_frame([
            {'ID da Tarefa':'ACT-026', 'Data da Visita':'01/10/2026',
             'Base':'Macaé/RJ','Descrição':'Visita pré marcada',
             'Pendências/Observações':'Consultoria rápida; troca de motor do portão.'},
            {'ID da Tarefa':'ACT-027', 'Data da Visita':'01/10/2026',
             'Base':'Macaé/RJ','Descrição':'Manutenção corretiva',
             'Pendências/Observações':'Detalhamento do circuito de força.'},
        ])
        result = visit_source_for_day(data,date(2026,10,1),'Macaé/RJ')
        self.assertEqual(result['ID da Tarefa vinculada'], 'ACT-026')
        self.assertEqual(result['Observações'], 'Consultoria rápida; troca de motor do portão.')

    def test_does_not_pull_another_day_or_base(self):
        data = task_frame([{'ID da Tarefa':'ACT-001','Data da Visita':'01/10/2026',
                            'Base':'Macaé/RJ','Descrição':'Visita pré marcada',
                            'Pendências/Observações':'Relato da base de Macaé'}])
        self.assertEqual(visit_source_for_day(data,date(2026,10,2),'Macaé/RJ')['Observações'],'')
        self.assertEqual(visit_source_for_day(data,date(2026,10,1),'Porto do Açu - São João da Barra/RJ')['Observações'],'')

    def test_complement_existing_visit_without_creating_duplicate(self):
        current={'ID da Visita':'VIS-0001','Data da Visita':'01/10/2026',
                 'Base':'Macaé/RJ','Tipo':'Presencial','ID da Tarefa vinculada':'ACT-026',
                 'Resumo':'Visita de rotina','Observações':'Relato anterior','Responsável':'',
                 'Origem':'Migração de tarefas (a validar)',
                 'Finalidade':'Rotina','Validação':'A validar'}
        dataset={'visits':[current]}
        with patch('storage.require_write'), patch('storage.demo_mode',return_value=True), \
             patch('storage._demo_data',return_value=dataset):
            update_visit('VIS-0001', dict(current),
                         {'Resumo':'Visita e acompanhamento','Observações':'Consultorias e orientações do dia',
                          'Validação':'Confirmada'})
        self.assertEqual(len(dataset['visits']),1)
        self.assertEqual(current['Data da Visita'],'01/10/2026')
        self.assertEqual(current['Observações'],'Consultorias e orientações do dia')
        self.assertEqual(current['Validação'],'Confirmada')

    def test_blank_visit_narrative_is_rejected(self):
        with patch('storage.require_write'):
            with self.assertRaises(ValueError):
                update_visit('VIS-0001',{}, {'Observações':'   '})

if __name__ == '__main__':
    unittest.main()
