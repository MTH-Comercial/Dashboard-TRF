import unittest
from datetime import date
import pandas as pd
from analytics import task_frame, sort_tasks_for_table, visits_from_tasks, contract_metrics, quality_issues, display_status

class DashboardRegressionTest(unittest.TestCase):
    def test_empty_planning_table_does_not_raise(self):
        self.assertTrue(sort_tasks_for_table(pd.DataFrame()).empty)
        d = task_frame([{'ID da Tarefa': 'ACT-001', 'Descricao': 'Teste', 'Status': 'Resolvido'}])
        self.assertTrue(sort_tasks_for_table(d.iloc[0:0]).empty)

    def test_missing_date_column_does_not_raise(self):
        d = pd.DataFrame([{'ID da Tarefa': 'ACT-002', 'Descrição':'Projeto técnico'}])
        self.assertEqual(len(sort_tasks_for_table(d)),1)

    def test_meeting_or_visit_completed_label(self):
        self.assertEqual(display_status('Reunião/alinhamento','Resolvido'),'Realizada')
        self.assertEqual(display_status('Visita de rotina','Resolvido'),'Realizada')
        self.assertEqual(display_status('Atividade técnica','Resolvido'),'Resolvido')

    def test_visit_counts_independent_of_work_type(self):
        d = task_frame([
          {'ID da Tarefa':'ACT-001','Descrição':'Manutenção emergencial','Base':'Macaé/RJ','Data da Visita':'04/11/2026'},
          {'ID da Tarefa':'ACT-002','Descrição':'Reunião de alinhamento','Base':'Macaé/RJ','Data da Visita':'04/11/2026'},
        ])
        visits = visits_from_tasks(d,date(2026,9,1),date(2027,8,31),date(2026,11,4))
        self.assertEqual(contract_metrics(visits)['total'],1)

    def test_diary_stage_differences_not_registration_errors(self):
        d=task_frame([{'ID da Tarefa':'ACT-001','Descrição':'Reunião','Fase':'Concluído','Status':'Em Andamento'}])
        self.assertEqual(len(quality_issues(d)),0)

if __name__ == '__main__':
    unittest.main()
