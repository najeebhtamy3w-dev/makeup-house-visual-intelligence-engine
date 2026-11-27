import unittest
from engine.candidate_ocr import assess_text
class CandidateOCRTests(unittest.TestCase):
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
