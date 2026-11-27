import unittest
from engine.identity_fusion import fuse

class FusionTests(unittest.TestCase):
    def test_agreement_not_verification(self):
        r=fuse({'brand':'Anua','size':'30ml'},[{'text':'ANUA 30 ml','score':.99}])
        self.assertEqual(r['fields']['brand']['status'],'OCR_CORROBORATED')
        self.assertFalse(r['verified'])
        self.assertFalse(r['size_conflict'])
    def test_conflict(self):
        r=fuse({'size':'140ml'},[{'text':'1000 ml','score':.95}])
        self.assertTrue(r['size_conflict'])
    def test_low_confidence(self):
        r=fuse({'brand':'YC'},[{'text':'YC','score':.3}])
        self.assertEqual(r['fields']['brand']['status'],'UNSUPPORTED')
