import unittest
from engine.search_strategy import queries,complete
class StrategyTests(unittest.TestCase):
    def test_queries(self):
        self.assertEqual(len(queries('Test Serum')),4)
    def test_coverage(self):
        a=dict(status='NEEDS_MANUAL_REVIEW',width=800,height=800,classification={'category_suggestion':'PACKSHOT'})
        b=dict(a,classification={'category_suggestion':'MARKETING'})
        self.assertFalse(complete([a]))
        self.assertTrue(complete([a,b]))
        self.assertFalse(complete([a,dict(b,status='SKU_CONFLICT')]))
        self.assertFalse(complete([a,dict(b,possible_duplicates=['x'])]))
