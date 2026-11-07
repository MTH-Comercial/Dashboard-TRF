"""Confere que a área administrativa oferece uma única navegação."""
import unittest
from pathlib import Path


class AdminMenuTest(unittest.TestCase):
    def test_single_menu_without_duplicated_actions(self):
        source = (Path(__file__).resolve().parents[1] / 'app.py').read_text(encoding='utf-8')
        self.assertNotIn('def admin_today():', source)
        self.assertNotIn("key='admin_today_kind'", source)
        admin = source.split('def render_admin():', 1)[1].split("\nif page==",1)[0]
        self.assertEqual(admin.count("key='admin_action'"), 1)
        for label in [
            'Registrar andamento ACT', 'Nova atividade ACT', 'Editar cadastro ACT',
            'Registrar visita VIS', 'Conferência / Exportação',
        ]:
            self.assertIn(label, admin)
        for target in [
            'admin_diary()', 'admin_new_task()', 'admin_edit_task()',
            'admin_visit()', 'admin_quality()',
        ]:
            self.assertIn(target, admin)
        self.assertNotIn('Lançar trabalho do dia', admin)


if __name__ == '__main__':
    unittest.main()
