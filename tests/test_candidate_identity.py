import unittest
from engine.candidate_identity import assess_candidate_identity

class CandidateIdentityTests(unittest.TestCase):
    def test_combined(self):
        row={'page_sku_evidence':[{'status':'CORROBORATED_REVIEW_REQUIRED'}],'visual_evidence':{'similarity_cosine':.91,'category':'packshot'}}
        self.assertEqual(assess_candidate_identity(row)['status'],'INSUFFICIENT_EVIDENCE')
        row['candidate_ocr']={'brand_supported':True,'size_supported':True,'required_text_supported':True}
        self.assertEqual(assess_candidate_identity(row)['status'],'CORROBORATED_REVIEW_REQUIRED')
        self.assertFalse(assess_candidate_identity(row)['identity_verified'])
        row['page_sku_conflict']=True
        self.assertEqual(assess_candidate_identity(row)['status'],'CONFLICT')
    def test_similarity_alone(self):
        self.assertEqual(assess_candidate_identity({'visual_evidence':{'similarity_cosine':.99,'category':'packshot'}})['status'],'INSUFFICIENT_EVIDENCE')
    def test_logo(self):
        self.assertEqual(assess_candidate_identity({'page_sku_evidence':[{'status':'CORROBORATED_REVIEW_REQUIRED'}],'visual_evidence':{'similarity_cosine':.99,'category':'logo'}})['status'],'INSUFFICIENT_EVIDENCE')
