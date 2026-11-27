import unittest
from engine.sku_evidence import compare
class EvidenceTests(unittest.TestCase):
    def test_units(self):
        a={'brand':'QV','name':'Wash','size':'1 l'}
        b={'brand':'qv','name':'Wash','size':'1000 ml'}
        r=compare(a,b)
        self.assertEqual(r['status'],'CORROBORATED_REVIEW_REQUIRED')
        self.assertFalse(r['verified'])
    def test_conflict(self):
        self.assertEqual(compare({'size':'1000 ml'},{'size':'140 ml'})['status'],'CONFLICT')
    def test_variant(self):
        self.assertEqual(compare({'variant':'Black'},{'variant':'Brown'})['status'],'CONFLICT')
    def test_missing(self):
        self.assertEqual(compare({'brand':'QV'},{})['status'],'INSUFFICIENT_EVIDENCE')
    def test_mass_volume(self):
        self.assertEqual(compare({'size':'100 g'},{'size':'100 ml'})['status'],'CONFLICT')
