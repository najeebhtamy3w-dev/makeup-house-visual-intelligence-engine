import unittest
from engine.sku_evidence import compare
class SKUAcceptanceMatrix(unittest.TestCase):
    def test_each_conflict(self):
        expected={'brand':'Anua','name':'Niacinamide serum','size':'30ml','variant':'10% + TXA 4%','gtin':'8801234567890'}
        for key,value in {'brand':'Other','name':'Retinol serum','size':'100ml','variant':'5%','gtin':'8801234567891'}.items():
            with self.subTest(field=key):
                result=compare(expected,{**expected,key:value})
                self.assertEqual(result['status'],'CONFLICT')
                self.assertIn(key,result['conflicts'])
                self.assertFalse(result['verified'])
        self.assertEqual(compare(expected,expected)['status'],'CORROBORATED_REVIEW_REQUIRED')
    def test_missing_is_not_match(self):
        result=compare({'brand':'Anua','name':'Serum','size':'30ml'},{'brand':'Anua'})
        self.assertEqual(result['status'],'INSUFFICIENT_EVIDENCE')
