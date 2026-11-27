import tempfile
import unittest
from pathlib import Path
from engine.batch_runtime import BatchRuntime

class BatchTests(unittest.TestCase):
    def test_retry_and_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'jobs.db'
            q=BatchRuntime(path)
            b=q.submit([{'kind':'a'},{'kind':'b'}])
            def handler(job,p):
                if p['kind']=='a': raise ValueError('fixture')
                return {'ok':True}
            q.run_next(handler); q.run_next(handler)
            self.assertEqual([r['state'] for r in q.status(b)],['FAILED','COMPLETED'])
            q=BatchRuntime(path)
            self.assertEqual(q.retry(b),1)
            q.run_next(lambda j,p:{'ok':True})
            self.assertEqual([r['state'] for r in q.status(b)],['COMPLETED','COMPLETED'])
    def test_limit(self):
        with tempfile.TemporaryDirectory() as d:
            q=BatchRuntime(Path(d)/'jobs.db')
            with self.assertRaises(ValueError): q.submit([{}]*101)
