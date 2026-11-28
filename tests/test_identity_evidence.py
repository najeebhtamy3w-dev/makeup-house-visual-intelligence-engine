import unittest
from engine.identity_evidence import collect
class Reader:
    def read(self,image):
        return [{'text':'4006381333931'}]
class Model:
    def identify(self,image):
        return {'fields':{'brand':'Test','name':'Serum'},'status':'UNVERIFIED_MODEL_HYPOTHESIS'}
class EvidenceTests(unittest.TestCase):
    def test_hypothesis_not_verified(self):
        r=collect(None,{},barcode=Reader(),multimodal=Model())
        self.assertEqual(r['query'],'Test Serum')
        self.assertNotIn('brand',r['fields'])
        self.assertEqual(r['fields']['barcode'],'04006381333931')
        self.assertFalse(r['commercial_approved'])
    def test_conflict(self):
        r=collect(None,{'barcode':'5901234123457'},barcode=Reader())
        self.assertEqual(r['status'],'IDENTITY_CONFLICT')
