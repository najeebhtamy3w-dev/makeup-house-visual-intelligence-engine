import tempfile
import unittest
from pathlib import Path
try:
    from fastapi.testclient import TestClient
    from engine.service_api import create_app
except ImportError:
    TestClient=None
from engine.batch_runtime import BatchRuntime

@unittest.skipIf(TestClient is None,'Service dependencies required')
class ApiTests(unittest.TestCase):
    def test_auth_and_batch(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            runtime=BatchRuntime(root/'db.sqlite')
            token='x'*32
            client=TestClient(create_app(runtime,root,token))
            headers={'Authorization':'Bearer '+token}
            self.assertEqual(client.get('/v1/health').status_code,401)
            self.assertEqual(client.get('/v1/health',headers=headers).status_code,200)
            response=client.post('/v1/batches',headers=headers,json={'jobs':[{'kind':'discover','query':'QV Wash'}]})
            self.assertEqual(response.status_code,200)
            batch=response.json()['batch_id']
            self.assertEqual(client.get('/v1/batches/'+batch,headers=headers).json()['jobs'][0]['state'],'QUEUED')
