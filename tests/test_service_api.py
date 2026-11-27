import tempfile
import io
import json
import hashlib
from PIL import Image
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

    def test_idempotent_batch_cancel_and_authenticated_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            runtime=BatchRuntime(root/'db.sqlite')
            client=TestClient(create_app(runtime,root,'x'*32))
            headers={'Authorization':'Bearer '+'x'*32,'Idempotency-Key':'stable-1'}
            payload={'jobs':[{'kind':'discover','query':'QV Wash'}]}
            first=client.post('/v1/batches',headers=headers,json=payload)
            again=client.post('/v1/batches',headers=headers,json=payload)
            self.assertEqual(first.json(),again.json())
            self.assertEqual(client.post('/v1/batches',headers=headers,json={'jobs':[{'kind':'discover','query':'other'}]}).status_code,409)
            batch=first.json()['batch_id']
            self.assertEqual(client.post('/v1/batches/'+batch+'/cancel',headers=headers).json()['cancelled'],1)
            self.assertEqual(runtime.status(batch)[0]['state'],'CANCELLED')
            self.assertEqual(client.get('/v1/openapi.json').status_code,401)
            schema=client.get('/v1/openapi.json',headers=headers).json()
            self.assertIn('/v1/batches',schema['paths'])
            self.assertEqual(client.get('/v1/health',headers={**headers,'Origin':'https://evil.example'}).status_code,403)
            huge=client.post('/v1/batches',headers=headers,content=b' '*1000001)
            self.assertEqual(huge.status_code,413)

    def test_authenticated_artifacts_hash_scope_and_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            runtime=BatchRuntime(root/'db.sqlite')
            client=TestClient(create_app(runtime,root,'x'*32))
            headers={'Authorization':'Bearer '+'x'*32}
            batch=runtime.submit([{'kind':'fixture'}])
            buffer=io.BytesIO()
            Image.new('RGB',(64,64),'gold').save(buffer,format='PNG')
            data=buffer.getvalue()
            def handler(job,payload):
                directory=root/'jobs'/job/('a'*32)
                directory.mkdir(parents=True)
                (directory/'edited.png').write_bytes(data)
                return {'artifact_directory':str(directory.relative_to(root)),'artifacts':{'edited.png':{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}}}
            job=runtime.run_next(handler)
            url='/v1/batches/'+batch+'/jobs/'+job+'/files/edited.png'
            response=client.get(url,headers=headers)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.content,data)
            self.assertEqual(response.headers['content-type'],'image/png')
            self.assertEqual(client.get(url).status_code,401)
            other=runtime.submit([{}])
            self.assertEqual(client.get('/v1/batches/'+other+'/jobs/'+job+'/files/edited.png',headers=headers).status_code,404)
            self.assertEqual(client.get(url.replace('edited.png','%2e%2e%2finput.png'),headers=headers).status_code,404)
            directory=root/'jobs'/job/('a'*32)
            (directory/'edited.png').write_bytes(b'tampered')
            self.assertEqual(client.get(url,headers=headers).status_code,409)
            (directory/'edited.png').unlink()
            outside=root/'private.png'
            outside.write_bytes(data)
            (directory/'edited.png').symlink_to(outside)
            self.assertEqual(client.get(url,headers=headers).status_code,404)

    def test_uploaded_source_hash_rechecked_by_handler(self):
        from engine.job_handler import JobHandler
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            runtime=BatchRuntime(root/'db.sqlite')
            client=TestClient(create_app(runtime,root,'x'*32))
            headers={'Authorization':'Bearer '+'x'*32}
            buffer=io.BytesIO()
            Image.new('RGB',(64,64),'red').save(buffer,format='PNG')
            identifier=client.post('/v1/inputs',headers=headers,content=buffer.getvalue()).json()['input']
            (root/'inputs'/identifier).write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'INPUT_HASH_MISMATCH'):
                JobHandler(root,lambda _:[],()).input(identifier)

    def test_export_hash_required_and_tamper_rejected(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            runtime=BatchRuntime(root/'db.sqlite')
            client=TestClient(create_app(runtime,root,'x'*32))
            headers={'Authorization':'Bearer '+'x'*32}
            batch=runtime.submit([{}])
            def handler(job,payload):
                folder=root/'jobs'/job
                folder.mkdir(parents=True)
                archive=folder/('b'*32+'.zip')
                with zipfile.ZipFile(archive,'w') as z:
                    z.writestr('manifest.json','{"publication_allowed":false}')
                return {'review_archive':archive.name,'review_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
            job=runtime.run_next(handler)
            url='/v1/batches/'+batch+'/jobs/'+job+'/export'
            self.assertEqual(client.get(url,headers=headers).status_code,200)
            (root/'jobs'/job/('b'*32+'.zip')).write_bytes(b'tampered')
            self.assertEqual(client.get(url,headers=headers).status_code,409)
