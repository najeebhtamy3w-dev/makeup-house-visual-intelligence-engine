import unittest
from engine.sku_verification import verify

class Reader:
    def read(self,image):
        return [{'text':image}]

class Broken:
    def read(self,image):
        raise RuntimeError('model unavailable')

class VerificationTests(unittest.TestCase):
    def test_missing_models(self):
        row=verify(None,None,{}, {})
        self.assertEqual(row['status'],'INSUFFICIENT_SKU_EVIDENCE')
        self.assertEqual(row['diagnostics']['encoder_status'],'NOT_CONFIGURED')
        self.assertFalse(row['commercial_approved'])

    def test_barcode_match(self):
        row=verify('4006381333931','4006381333931',{}, {},barcode_reader=Reader())
        self.assertEqual(row['status'],'BARCODE_MATCH_REVIEW_REQUIRED')

    def test_conflicting_image_barcode(self):
        row=verify('4006381333931','4006381333931',{}, {'barcode':'5901234123457'},barcode_reader=Reader())
        self.assertEqual(row['status'],'SKU_CONFLICT')

    def test_model_failure(self):
        row=verify(None,None,{}, {},ocr_reader=Broken())
        self.assertIn('reference_ocr_error',row['diagnostics'])
        self.assertFalse(row['commercial_approved'])
