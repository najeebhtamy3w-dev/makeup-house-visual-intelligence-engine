import unittest
from engine.ranking import rank_candidates

class RankingTests(unittest.TestCase):
    def test_order_and_exclusion(self):
        rows=[dict(status='NEEDS_MANUAL_REVIEW',width=500,height=500,sha256='a'),dict(status='NEEDS_MANUAL_REVIEW',width=900,height=900,sha256='b'),dict(status='SKU_CONFLICT',width=1200,height=1200,sha256='c'),dict(status='NEEDS_MANUAL_REVIEW',width=200,height=200,sha256='d')]
        result=rank_candidates(rows)
        self.assertEqual([x['sha256'] for x in result],['b','a'])
        self.assertTrue(all(not x['commercial_approved'] for x in result))
