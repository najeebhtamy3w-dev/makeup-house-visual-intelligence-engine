import unittest
from engine.adaptive_identity import identify_adaptive

class AdaptiveTests(unittest.TestCase):
    def test_search_before_visual(self):
        calls=[]
        lines=[{'text':x,'score':.99} for x in ['Anua','Serum','30 ml']]
        def search(q):
            calls.append('search')
            return ['candidate']
        def visual():
            calls.append('visual')
            return {'fields':{'brand':'Anua'}}
        result=identify_adaptive(lines,visual,search)
        self.assertEqual(calls,['search','visual'])
        self.assertFalse(result['adaptive']['verified'])
    def test_weak_evidence(self):
        result=identify_adaptive([],lambda:{'fields':{'brand':'QV'}},lambda q:self.fail('unexpected search'))
        self.assertFalse(result['adaptive']['search_attempted'])
    def test_search_failure_fallback(self):
        def search(q):
            raise TimeoutError()
        result=identify_adaptive([{'text':x,'score':.99} for x in ['Anua','Serum','30 ml']],lambda:{'fields':{'brand':'Anua'}},search)
        self.assertEqual(result['adaptive']['search_error'],'TimeoutError')
        self.assertTrue(result['adaptive']['visual_executed'])

    def test_external_size_conflict(self):
        result=identify_adaptive([],lambda:{'fields':{'brand':'QV','size':'140 ml'}},structured_evidence=[{'source':'catalog','fields':{'brand':'QV','size':'1000 ml'}}])
        self.assertEqual(result['sku_evidence'][0]['comparison']['status'],'CONFLICT')
        self.assertFalse(result['identity_verified'])
