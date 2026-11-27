import unittest
from engine.identity_fusion import fuse

class FusionTests(unittest.TestCase):
    def test_short_brands_are_tokens_and_invalid_confidence_is_ignored(self):
        for brand in ('QV','YC'):
            self.assertEqual(fuse({'brand':brand},[{'text':brand,'score':.95}])['fields']['brand']['status'],'OCR_CORROBORATED')
            self.assertEqual(fuse({'brand':brand},[{'text':brand+'Plus','score':.95}])['fields']['brand']['status'],'UNSUPPORTED')
        from engine.identity_fusion import strong_lines
        self.assertEqual(strong_lines([{'text':'bad','score':float('inf')},{'text':'bad','score':'no'}, {'text':'bad','score':True}, {'text':'good','score':.95}]),['good'])

    def test_dual_unit_label_and_metric_equivalence(self):
        r=fuse({'size':'6 fl oz (178 ml)'},[{'text':'178ml','score':.95}])
        self.assertFalse(r['size_conflict'])
        self.assertEqual(r['fields']['size']['status'],'OCR_CORROBORATED')
        from engine.identity_fusion import canonical_size
        self.assertEqual(canonical_size('1 kg'),canonical_size('1000 g'))
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

    def test_noisy_unit(self):
        r=fuse({'size':'140ml'},[{'text':'1000 m1','score':.95}])
        self.assertTrue(r['size_conflict'])
        self.assertFalse(r['verified'])
    def test_routing(self):
        from engine.identity_fusion import route
        self.assertEqual(route([])['route'],'QWEN_REQUIRED')
        self.assertEqual(route([{'text':x,'score':.95} for x in ['Anua','Serum','30 ml']])['route'],'EXTERNAL_SEARCH_FIRST')
    def test_fuzzy_not_verified(self):
        r=fuse({'brand':'Vit Gold'},[{'text':'VEETgold','score':.95}])
        self.assertGreater(r['fields']['brand']['approximate_match'],0)
        self.assertFalse(r['verified'])
