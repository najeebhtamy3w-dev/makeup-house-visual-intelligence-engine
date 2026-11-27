import unittest,tempfile
from pathlib import Path
from PIL import Image
from engine.direct_edit_qa import assess_edit

class DirectEditQATests(unittest.TestCase):
    def test_missing_models_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'image.png'
            Image.new('RGB',(64,64)).save(p)
            result=assess_edit(p,p)
            self.assertFalse(result['publication_allowed'])
            self.assertFalse(result['identity_verified'])
            self.assertIn('OCR_QA_UNAVAILABLE',result['warnings'])
    def test_low_similarity(self):
        class Evaluator:
            def for_reference(self,path):
                return lambda output,query:{'similarity_cosine':.4}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'image.png'
            Image.new('RGB',(64,64)).save(p)
            self.assertIn('LOW_VISUAL_SIMILARITY',assess_edit(p,p,Evaluator())['warnings'])
    def test_nonfinite_similarity_is_invalid_not_usable_evidence(self):
        import json
        class Evaluator:
            def __init__(self,value): self.value=value
            def for_reference(self,path):
                return lambda output,query:{'similarity_cosine':self.value}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'image.png'; Image.new('RGB',(64,64)).save(p)
            for value in (float('nan'),float('inf'),-float('inf'),1.2,-1.2,None,True,'0.95'):
                with self.subTest(value=value):
                    result=assess_edit(p,p,Evaluator(value))
                    self.assertIn('VISUAL_SIMILARITY_INVALID',result['warnings'])
                    self.assertEqual(result['visual_evidence_status'],'INVALID')
                    self.assertFalse(result['identity_verified'])
                    json.dumps(result,allow_nan=False)

    def test_ocr_reports_changed_size_and_concentration_without_masks(self):
        class Reader:
            def predict(self,path):
                text='QV cleanser 140 ml 5%' if path.endswith('source.png') else 'QV cleanser 1000 ml 10%'
                class Page:
                    json={'res':{'rec_texts':[text],'rec_scores':[.98]}}
                return [Page()]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in ('source.png','output.png'): Image.new('RGB',(64,64)).save(root/name)
            result=assess_edit(root/'source.png',root/'output.png',ocr=Reader())
            self.assertIn('PRODUCT_NUMERIC_TEXT_MAY_HAVE_CHANGED',result['warnings'])
            self.assertEqual(result['ocr_missing_quantities'],[{'value':'140','unit':'ml'},{'value':'5','unit':'%'}])
            self.assertEqual(result['ocr_added_quantities'],[{'value':'10','unit':'%'},{'value':'1000','unit':'ml'}])
            self.assertFalse(result['publication_allowed'])

    def test_equivalent_numeric_formats_do_not_report_quantity_change(self):
        class Reader:
            def predict(self,path):
                text='١٤٠ مل ٥٫٠٪ 0.14 l' if path.endswith('source.png') else '140ml 5% 140 ml'
                class Page:
                    json={'res':{'rec_texts':[text],'rec_scores':[.99]}}
                return [Page()]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in ('source.png','output.png'): Image.new('RGB',(64,64)).save(root/name)
            result=assess_edit(root/'source.png',root/'output.png',ocr=Reader())
            self.assertNotIn('PRODUCT_NUMERIC_TEXT_MAY_HAVE_CHANGED',result['warnings'])
            self.assertEqual(result['ocr_missing_quantities'],[])
            self.assertEqual(result['ocr_added_quantities'],[])

    def test_ambiguous_thousands_comma_is_not_treated_as_decimal_fact(self):
        class Reader:
            def predict(self,path):
                text='1,000 ml' if path.endswith('source.png') else '1 ml'
                class Page:
                    json={'res':{'rec_texts':[text],'rec_scores':[.99]}}
                return [Page()]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in ('source.png','output.png'): Image.new('RGB',(64,64)).save(root/name)
            result=assess_edit(root/'source.png',root/'output.png',ocr=Reader())
            self.assertIn('AMBIGUOUS_NUMERIC_FORMAT_REQUIRES_REVIEW',result['warnings'])
            self.assertIn('PRODUCT_NUMERIC_TEXT_MAY_HAVE_CHANGED',result['warnings'])
