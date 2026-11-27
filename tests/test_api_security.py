import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient
from engine.service_api import create_app
from engine.batch_runtime import BatchRuntime

class SecurityTests(unittest.TestCase):
    def test_negative_and_duplicate_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            client=TestClient(create_app(BatchRuntime(root/'db'),root,'x'*32))
            h={'Authorization':'Bearer '+'x'*32}
            self.assertEqual(client.post('/v1/inputs',content=b'bad').status_code,401)
            self.assertEqual(client.post('/v1/inputs',headers=h,content=b'bad').status_code,422)
            self.assertEqual(client.post('/v1/inputs',headers=h,content=b'x'*10000001).status_code,413)
            for value,status in [('../secret',422),('a'*64+'.png',404)]:
                self.assertEqual(client.post('/v1/batches',headers=h,json={'jobs':[{'kind':'identify','input':value}]}).status_code,status)
            b=io.BytesIO()
            Image.new('RGB',(64,64)).save(b,format='PNG')
            a=client.post('/v1/inputs',headers=h,content=b.getvalue())
            c=client.post('/v1/inputs',headers=h,content=b.getvalue())
            self.assertEqual(a.status_code,200)
            self.assertEqual(a.json(),c.json())
            self.assertEqual(len(list((root/'inputs').iterdir())),1)
