import tempfile,unittest
from pathlib import Path
from engine.batch import Batch

class BatchTests(unittest.TestCase):
    def test_resume_dedup_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p=root/'input'
            p.write_bytes(b'fixture')
            b=Batch(root/'queue')
            key=b.add('serum',p)
            self.assertEqual(key,b.add('serum',p))
            def fail(*args): raise RuntimeError('network')
            self.assertEqual(b.run(fail),{'FAILED':1})
            b.close()
            b=Batch(root/'queue')
            self.assertEqual(b.run(lambda p,f:{'status':'REVIEW_REQUIRED'}),{'REVIEW_REQUIRED':1})
            self.assertEqual(b.run(fail),{'REVIEW_REQUIRED':1})
            b.close()
