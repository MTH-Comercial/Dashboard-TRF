"""Regras do painel executivo: subáreas ACT e divergências do último evento."""
import unittest
from pathlib import Path
from analytics import (
    task_frame, diary_frame, technical_activities_by_subarea,
    latest_update_conflicts,
)


class ExecutiveSubareasTests(unittest.TestCase):
    def test_count_technical_tasks_not_visits_meetings_or_radar(self):
        tasks=task_frame([
            {'ID da Tarefa':'ACT-001','Descrição':'Instalar nobreak','Subárea':'Portaria',
             'Tipo de Registro':'Atividade técnica','Status':'Resolvido'},
            {'ID da Tarefa':'ACT-002','Descrição':'Trocar proteção','Subárea':'Portaria',
             'Tipo de Registro':'Atividade técnica','Status':'Em Andamento'},
            {'ID da Tarefa':'ACT-003','Descrição':'Manutenção no Blend','Subárea':'Blend',
             'Tipo de Registro':'Atividade técnica','Status':'Pausado'},
            {'ID da Tarefa':'ACT-004','Descrição':'Visita de emergência','Subárea':'Blend',
             'Tipo de Registro':'Atividade técnica','Status':'Resolvido'},
            {'ID da Tarefa':'ACT-005','Descrição':'Reunião de alinhamento','Subárea':'Portaria',
             'Tipo de Registro':'Reunião/alinhamento','Status':'Realizado'},
            {'ID da Tarefa':'ACT-006','Descrição':'Estudo futuro','Subárea':'Portaria',
             'Tipo de Registro':'Demanda no radar','Status':'Não Iniciado'},
        ])
        result=technical_activities_by_subarea(tasks)
        self.assertEqual(result['Quantidade'].sum(), 3)
        amounts={(r['Subárea'],r['Situação']):r['Quantidade'] for _,r in result.iterrows()}
        self.assertEqual(amounts[('Portaria','Concluídas')],1)
        self.assertEqual(amounts[('Portaria','Em execução')],1)
        self.assertEqual(amounts[('Blend','Aguardando/bloqueadas')],1)

    def test_no_false_conflict_from_earlier_history_phase(self):
        tasks=task_frame([
            {'ID da Tarefa':'ACT-013','Descrição':'Instalação de nobreak',
             'Fase':'Concluído','Status':'Resolvido'}])
        diary=diary_frame([
            {'Data da Atualização':'2026-09-01','ID da Tarefa':'ACT-013',
             'Fase Atualizada':'Em Execução','Status Atualizado':'Em Andamento'},
            {'Data da Atualização':'2026-09-17','ID da Tarefa':'ACT-013',
             'Fase Atualizada':'Concluído','Status Atualizado':'Resolvido'},
        ])
        self.assertTrue(latest_update_conflicts(tasks,diary).empty)

    def test_stale_main_task_detected_without_overwriting_history(self):
        tasks=task_frame([
            {'ID da Tarefa':'ACT-013','Descrição':'Instalação de nobreak',
             'Fase':'Em Execução','Status':'Em Andamento'}])
        diary=diary_frame([
            {'Data da Atualização':'2026-09-17','ID da Tarefa':'ACT-013',
             'Fase Atualizada':'Concluído','Status Atualizado':'Resolvido'}])
        conflicts=latest_update_conflicts(tasks,diary)
        self.assertEqual(len(conflicts),1)
        self.assertEqual(conflicts.iloc[0]['Status na última atualização'],'Resolvido')
        self.assertEqual(tasks.iloc[0]['Status'],'Em Andamento')

    def test_executive_chart_is_scoped_to_technical_activities(self):
        source=(Path(__file__).resolve().parents[1]/'app.py').read_text(encoding='utf-8')
        self.assertIn('technical_activities_by_subarea(filtered)',source)
        self.assertIn('latest_update_conflicts(tasks, diary)',source)
        self.assertIn('O gráfico mede registros, NÃO horas',source)


if __name__ == '__main__':
    unittest.main()
