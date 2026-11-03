import unittest
from datetime import date
from analytics import (task_frame, visit_frame, task_metrics, visits_from_tasks,
                       visits_from_register, contract_window, contract_metrics,
                       new_task_id, quality_issues)
from security import hash_password, verify_password, safe_user_entry

class RulesTest(unittest.TestCase):
    def setUp(self):
        self.tasks = task_frame([
            {'ID da Tarefa':'ACT-001','Data de Início':'01/09/2026','Data da Visita':'02/09/2026',
             'Base':'Macaé/RJ','Status':'Resolvido','Fase':'Concluído','Prioridade':'Rotina'},
            {'ID da Tarefa':'ACT-002','Data de Início':'02/09/2026','Data da Visita':'02/09/2026',
             'Base':'Macaé/RJ','Status':'Em Andamento','Fase':'Em Execução','Prioridade':'Emergencial',
             'Previsão de Conclusão':'10/09/2026'},
            {'ID da Tarefa':'ACT-003','Data de Início':'02/09/2026','Data da Visita':'02/09/2026',
             'Base':'Porto do Açu - São João da Barra/RJ','Status':'Em Andamento','Fase':'Concluído'},
        ])

    def test_visits_dedup_by_date_and_unit(self):
        v = visits_from_tasks(self.tasks, date(2026,9,1), date(2027,8,31),date(2026,11,3))
        self.assertEqual(contract_metrics(v)['total'], 2)
        self.assertEqual(contract_metrics(v)['macae'], 1)

    def test_registry_replaces_legacy(self):
        v = visit_frame([{'ID da Visita':'VIS-0001','Data da Visita':'02/09/2026',
                          'Base':'Macaé/RJ','Tipo':'Presencial'},
                         {'ID da Visita':'VIS-0002','Data da Visita':'03/09/2026',
                          'Base':'Macaé/RJ','Tipo':'Remoto'}])
        self.assertEqual(len(visits_from_register(v,date(2026,9,1),date(2027,8,31),date(2026,11,3))),1)

    def test_overdue(self):
        k = task_metrics(self.tasks,date(2026,11,3))
        self.assertEqual(k['total'],3)
        self.assertEqual(k['overdue'],1)
        self.assertEqual(len(quality_issues(self.tasks)),1)

    def test_id_and_cycle(self):
        self.assertEqual(new_task_id(['ACT-001','ACT-019']), 'ACT-020')
        self.assertEqual(contract_window('2026-09-01',date(2026,11,3)),(date(2026,9,1),date(2027,8,31)))

    def test_password_and_formulas(self):
        pw = hash_password('SenhaTemporaria123!')
        self.assertTrue(verify_password('SenhaTemporaria123!',pw))
        self.assertFalse(verify_password('errada',pw))
        self.assertEqual(safe_user_entry('=IMPORTXML("url")'),"'=IMPORTXML(\"url\")")

if __name__ == '__main__':
    unittest.main()
