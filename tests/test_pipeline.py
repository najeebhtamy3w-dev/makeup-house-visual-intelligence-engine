import io
import unittest
from PIL import Image
from engine.pipeline import run_product

class Client:
    allowed_hosts=('example.com',)
    def fetch(self,url,limit,mime):
        if mime=='text/html':
            return b'<img src="/a.png"><img src="/b.png">','text/html',url
        out=io.BytesIO()
        Image.new('RGB',(500,500),'white').save(out,format='PNG')
        return out.getvalue(),'image/png',url

class PipelineTests(unittest.TestCase):
    def test_integrated_review_and_duplicates(self):
        report=run_product('serum',Image.new('RGB',(500,500)),{},Client(),seeds=['https://example.com/product'])
        self.assertEqual(report['status'],'REVIEW_REQUIRED')
        self.assertEqual(len(report['images']),2)
        self.assertEqual(report['images'][1]['status'],'EXACT_DUPLICATE')
        self.assertFalse(report['commercial_approved'])
    def test_budget(self):
        report=run_product('serum',None,{},Client(),seeds=['https://example.com/product'],max_images=1)
        self.assertEqual(len(report['images']),1)
