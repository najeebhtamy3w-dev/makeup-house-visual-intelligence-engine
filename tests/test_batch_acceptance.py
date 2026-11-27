import tempfile
import unittest
from pathlib import Path
from engine.batch_runtime import BatchRuntime

class BatchAcceptance(unittest.TestCase):
    def test_scales_and_retry(self):
        for count in (10,30,100):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as d:
                path=Path(d)/'jobs.db'
                runtime=BatchRuntime(path)
                batch=runtime.submit([{'index':i} for i in range(count)])
                seen=set()
                def handler(job,payload):
                    if payload['index']==0 and job not in seen:
                        seen.add(job)
                        raise RuntimeError('fixture failure')
                    seen.add(job)
                    return {'index':payload['index'],'publication_allowed':False}
                for _ in range(count):
                    self.assertIsNotNone(runtime.run_next(handler))
                self.assertIsNone(runtime.run_next(handler))
                runtime=BatchRuntime(path)
                self.assertEqual(sum(r['state']=='FAILED' for r in runtime.status(batch)),1)
                self.assertEqual(runtime.retry(batch),1)
                runtime.run_next(handler)
                rows=runtime.status(batch)
                self.assertEqual(len(rows),count)
                self.assertEqual(len(seen),count)
                self.assertTrue(all(r['state']=='COMPLETED' for r in rows))
                self.assertEqual(sum(r['attempts'] for r in rows),count+1)
