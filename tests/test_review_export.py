import tempfile
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from engine.review_export import export_review
from engine.brand_profiles import campaign_prompt

class ReviewTests(unittest.TestCase):
    def test_private_archive(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); src=p/'images'; src.mkdir()
            Image.new('RGB',(32,32)).save(src/'edited.png')
            report=export_review(src,p/'review.zip',{})
            self.assertFalse(report['publication_allowed'])
            with zipfile.ZipFile(p/'review.zip') as z:
                self.assertEqual(set(z.namelist()),{'images/edited.png','manifest.json'})
    def test_brand(self):
        self.assertNotEqual(campaign_prompt('makeup_house','test'),campaign_prompt('unwan_al_atr','test'))
        with self.assertRaises(ValueError): campaign_prompt('unknown','test')
