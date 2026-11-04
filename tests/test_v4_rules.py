import unittest
from datetime import date
from analytics import infer_record_kind, task_frame, display_status, visits_from_register, contract_metrics, visit_frame, quality_issues, is_radar

class V4Tests(unittest.TestCase):
    def test_meetings_and_visits_are_not_deliveries(self):
        self.assertEqual(infer_record_kind('Visita e reunião de alinhamento'),'Reunião/alinhamento')
        self.assertEqual(infer_record_kind('Visita de emergencia para acompanhamento técnico'),'Acompanhamento de campo')
        self.assertEqual(display_status('Reunião/alinhamento','Resolvido'),'Realizada')

    def test_historical_phase_transition_is_not_error(self):
        df=task_frame([{'ID da Tarefa':'ACT-001','Descrição':'Manutenção corretiva',
            'Fase':'Em Execução','Status':'Resolvido','Data de Início':'02/11/2026'}])
        self.assertTrue(quality_issues(df).empty)

    def test_estimated_visits_and_discarded_records(self):
        df=visit_frame([
          {'ID da Visita':'VIS-001','Data da Visita':'02/11/2026','Base':'Macaé/RJ',
           'Tipo':'Presencial','Finalidade':'Reunião/alinhamento','Validação':'A validar'},
          {'ID da Visita':'VIS-002','Data da Visita':'03/11/2026','Base':'Macaé/RJ',
           'Tipo':'Presencial','Finalidade':'Atendimento emergencial','Validação':'Confirmada'},
          {'ID da Visita':'VIS-003','Data da Visita':'04/11/2026','Base':'Macaé/RJ',
           'Tipo':'Presencial','Finalidade':'Rotina','Validação':'Descartada'},
        ])
        visits=visits_from_register(df,date(2026,9,1),date(2027,8,31),date(2026,11,4))
        self.assertEqual(contract_metrics(visits)['macae'],2)

    def test_radar_does_not_auto_include_meeting(self):
        df=task_frame([
          {'ID da Tarefa':'ACT-001','Descrição':'Reunião de alinhamento com gestores',
           'Status':'Em Andamento','Prioridade':'Planejamento (Futuro)'},
          {'ID da Tarefa':'ACT-002','Descrição':'Projeto SPDA','Status':'Em Andamento',
           'Prioridade':'Planejamento (Futuro)'},
        ])
        self.assertFalse(is_radar(df.iloc[0]))
        self.assertTrue(is_radar(df.iloc[1]))

if __name__=='__main__': unittest.main()
