import hashlib,tempfile,unittest
from pathlib import Path
from PIL import Image
from engine.studio_job import prepare

class StudioJobTests(unittest.TestCase):
    def test_prepare_and_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source.png'
            Image.new('RGB',(500,500),'red').save(p)
            row=dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),url='https://example.org/image')
            report=dict(ranked_candidates=[row])
            results=prepare(report,tmp)
            self.assertEqual(len(results),2)
            self.assertTrue(all(not x['commercial_approved'] for x in results))
            self.assertEqual(Image.open(Path(tmp)/results[1]['file']).size,(1080,1920))
            p.write_bytes(b'tampered')
            self.assertEqual(prepare(report,tmp)[0]['status'],'STUDIO_FAILED')
