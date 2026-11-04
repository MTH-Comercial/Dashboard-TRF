import unittest
from datetime import date
from analytics import task_frame, delivery_overview, delivery_frame, is_radar, infer_record_kind
from preview import parse_uploaded_workbook

class ClassificationTest(unittest.TestCase):
    def test_conservative_legacy_inference(self):
        self.assertEqual(infer_record_kind('Visita pré marcada'), 'Visita de rotina')
        self.assertEqual(infer_record_kind('Visita pré-marcada'), 'Visita de rotina')
        self.assertEqual(infer_record_kind('Reunião de alinhamento com cliente'), 'Reunião/alinhamento')
        self.assertEqual(infer_record_kind('Visita de emergência para manutenção da prensa'), 'Atividade técnica')

    def test_visits_do_not_inflate_deliveries_and_deadlines_not_overstated(self):
        rows = [
          {'ID da Tarefa': 'ACT-001','Descrição':'Visita pré marcada','Status':'Resolvido','Prioridade':'Rotina','Data de Início':'01/09/2026'},
          {'ID da Tarefa': 'ACT-002','Descrição':'Reunião geral','Status':'Resolvido','Data de Início':'01/09/2026'},
          {'ID da Tarefa': 'ACT-003','Descrição':'Manutenção elétrica','Status':'Resolvido','Data de Início':'01/09/2026'},
          {'ID da Tarefa': 'ACT-004','Descrição':'Projeto eletrico','Status':'Aguardando Terceiros','Previsão de Conclusão':'01/10/2026','Data de Início':'01/09/2026'},
          {'ID da Tarefa': 'ACT-005','Descrição':'Implantação SCADA','Status':'Em Andamento','Previsão de Conclusão':'01/10/2026','Condição do Prazo':'Compromisso confirmado','Data de Início':'01/09/2026'},
        ]
        df = task_frame(rows)
        k = delivery_overview(df, date(2026, 11, 4))
        self.assertEqual(k['deliveries'],3)
        self.assertEqual(k['done'],1)
        self.assertEqual(k['routine_visits'],1)
        self.assertEqual(k['meetings'],1)
        self.assertEqual(k['waiting'],1)
        self.assertEqual(k['late_commitments'],1)
        self.assertEqual(df.loc[df['ID da Tarefa']=='ACT-004','Condição do Prazo'].iloc[0],'Histórico sem classificação')

    def test_radar_resolved_not_in_queue(self):
        tasks = task_frame([
          {'ID da Tarefa':'ACT-001','Descrição':'Projeto MT','Status':'Em Andamento','Prioridade':'Planejamento (Futuro)'},
          {'ID da Tarefa':'ACT-002','Descrição':'Projeto BT','Status':'Resolvido','Prioridade':'Planejamento (Futuro)'},
        ])
        self.assertTrue(is_radar(tasks.iloc[0]))
        self.assertFalse(is_radar(tasks.iloc[1]))

if __name__=='__main__': unittest.main()

