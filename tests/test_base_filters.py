"""Regressões do filtro de bases (ACT independente de VIS)."""
import unittest
import pandas as pd
from analytics import BASES, base_filter_options

class FilterBaseOptionsTests(unittest.TestCase):
    def test_acu_from_vis_when_tasks_only_macae(self):
        tasks = pd.DataFrame({'Base':['Macaé/RJ','Macaé/RJ','']})
        visits = pd.DataFrame({'Base':['Macaé/RJ','Porto do Açu - São João da Barra/RJ']})
        result = base_filter_options(tasks,visits)
        self.assertEqual(result[:3], BASES[:3])
        self.assertEqual(result.count('Porto do Açu - São João da Barra/RJ'),1)

    def test_gradim_is_available_without_any_visits_or_tasks(self):
        result=base_filter_options(pd.DataFrame({'Base':['Macaé/RJ']}),pd.DataFrame({'Base':[]}))
        self.assertIn('Gradim - São Gonçalo/RJ',result)
        self.assertNotIn('A definir',result)

    def test_real_additional_base_is_preserved_and_empty_ignored(self):
        tasks=pd.DataFrame({'Base':['Macaé/RJ',None,'Outro Polo/RJ']})
        visits=pd.DataFrame({'Base':['','Outro Polo/RJ','nan']})
        result=base_filter_options(tasks,visits)
        self.assertEqual(result.count('Outro Polo/RJ'),1)
        self.assertNotIn('',result)
        self.assertNotIn('nan',result)

    def test_missing_base_column_is_safe(self):
        self.assertEqual(base_filter_options(pd.DataFrame(),None),BASES[:-1])

if __name__=='__main__':
    unittest.main()
