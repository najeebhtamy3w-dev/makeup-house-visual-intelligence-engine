import unittest
from engine.candidate_ocr import assess_text
class CandidateOCRTests(unittest.TestCase):
    def test_short_brand_exact_tokens_and_required_variant(self):
        fields={'brand':'QV','name':'Gentle Wash','size':'1 l','variant':'Sensitive'}
        r=assess_text(fields,[{'text':'QV Gentle Wash Sensitive 1000 ml','score':.95}])
        self.assertTrue(r['brand_supported'])
        self.assertTrue(r['required_text_supported'])
        self.assertTrue(r['size_supported'])
        r=assess_text(fields,[{'text':'QVC Gentle Wash 1000 ml','score':.95}])
        self.assertFalse(r['brand_supported'])
        self.assertFalse(r['required_text_supported'])

    def test_gtin_conflicts_and_ambiguous_sizes(self):
        r=assess_text({'gtin':'4006381333931','size':'30ml'},[{'text':'5901234123457 30 ml 100 ml','score':.95}])
        self.assertTrue(r['gtin_conflict'])
        self.assertTrue(r['size_review_required'])

    def test_matching(self):
        result=assess_text({'brand':'Anua','size':'30ml'},[{'text':'ANUA 30 ml','score':.95}])
        self.assertTrue(result['brand_supported'])
        self.assertTrue(result['size_supported'])
        self.assertFalse(result['identity_verified'])
    def test_mismatch(self):
        result=assess_text({'brand':'Anua','size':'30ml'},[{'text':'ANUA 100 ml','score':.95}])
        self.assertTrue(result['size_review_required'])
    def test_uncertain(self):
        result=assess_text({'brand':'Anua','size':'30ml'},[{'text':'ANUA 100 ml','score':.2}])
        self.assertFalse(result['size_review_required'])
        self.assertFalse(result['brand_supported'])
