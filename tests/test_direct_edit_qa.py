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
