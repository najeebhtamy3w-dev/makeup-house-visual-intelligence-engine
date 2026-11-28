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

    def test_idempotency_persists_and_conflicts(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'jobs.db'
            q=BatchRuntime(path)
            batch=q.submit([{'kind':'discover','query':'QV'}],idempotency_key='request-1')
            q=BatchRuntime(path)
            self.assertEqual(q.submit([{'query':'QV','kind':'discover'}],idempotency_key='request-1'),batch)
            with self.assertRaisesRegex(ValueError,'IDEMPOTENCY_CONFLICT'):
                q.submit([{'kind':'discover','query':'other'}],idempotency_key='request-1')
            self.assertEqual(len(q.status(batch)),1)

    def test_cancel_during_processing_does_not_complete(self):
        with tempfile.TemporaryDirectory() as d:
            q=BatchRuntime(Path(d)/'jobs.db')
            batch=q.submit([{'kind':'test'}])
            def handler(job,payload):
                self.assertEqual(q.cancel(batch),1)
                return {'output':'stale'}
            q.run_next(handler)
            row=q.status(batch)[0]
            self.assertEqual(row['state'],'CANCELLED')
            self.assertIsNone(row['result'])
            self.assertEqual(q.retry(batch),1)
            q.run_next(lambda *_:{'output':'fresh'})
            self.assertEqual(q.status(batch)[0]['state'],'COMPLETED')

    def test_recovery_retry_prevents_old_attempt_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            q=BatchRuntime(Path(d)/'jobs.db')
            batch=q.submit([{'kind':'test'}])
            def old_handler(job,payload):
                self.assertEqual(q.recover_interrupted(),1)
                q.retry(batch)
                q.run_next(lambda *_:{'output':'new'})
                return {'output':'old'}
            q.run_next(old_handler)
            import json
            row=q.status(batch)[0]
            self.assertEqual(json.loads(row['result'])['output'],'new')
            self.assertEqual(row['attempts'],2)

    def test_explicit_engine_error_and_private_failure(self):
        with tempfile.TemporaryDirectory() as d:
            q=BatchRuntime(Path(d)/'jobs.db')
            batch=q.submit([{},{}])
            def unavailable(*_): raise RuntimeError('STUDIO_UNAVAILABLE')
            q.run_next(unavailable)
            def private(*_): raise ValueError('/private/path/token-secret')
            q.run_next(private)
            self.assertEqual([row['error'] for row in q.status(batch)],['STUDIO_UNAVAILABLE','ValueError'])

    def test_worker_lease_blocks_recovery_when_active(self):
        from engine.service_main import worker_lease
        with tempfile.TemporaryDirectory() as d:
            with worker_lease(d):
                with self.assertRaisesRegex(RuntimeError,'WORKER_ALREADY_ACTIVE'):
                    worker_lease(d)
            with worker_lease(d): pass
