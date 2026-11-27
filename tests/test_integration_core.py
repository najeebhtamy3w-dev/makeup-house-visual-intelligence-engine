import io
import tempfile
import unittest
from PIL import Image
from engine.integration_core import discover

class FakeDownloader:
    def fetch(self,url,limit,mime):
        if mime=='text/html':
            return b'<img src="https://example.com/a.png"><img src="https://example.com/b.png">','text/html',url
        out=io.BytesIO()
        Image.new('RGB',(640,640),'red').save(out,format='PNG')
        return out.getvalue(),'image/png',url

class IntegrationTest(unittest.TestCase):
    def test_discovery_deduplicates_and_blocks_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            result=discover('test',lambda q:[{'url':'https://example.com/product'}],['example.com'],folder,downloader=FakeDownloader())
            self.assertEqual(len(result['candidates']),1)
            self.assertEqual(result['attempts'],2)
            self.assertFalse(result['publication_allowed'])
            self.assertFalse(result['candidates'][0]['identity_verified'])
    def test_empty(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(discover('test',lambda q:[],[],folder)['status'],'NO_CANDIDATES')
