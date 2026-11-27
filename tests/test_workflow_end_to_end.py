import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient
from engine.service_api import create_app
from engine.batch_runtime import BatchRuntime
from engine.job_handler import JobHandler

class Editor:
    def edit(self,image,prompt,seed): return Image.new('RGB',image.size,'blue')
class Segmenter:
    def segment(self,image):
        mask=Image.new('L',image.size)
        mask.paste(255,(20,20,44,44))
        return mask

class EndToEnd(unittest.TestCase):
    def test_studio_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            runtime=BatchRuntime(root/'jobs.db')
            client=TestClient(create_app(runtime,root,'x'*32))
            headers={'Authorization':'Bearer '+'x'*32}
            buf=io.BytesIO()
            Image.new('RGB',(64,64),'red').save(buf,format='PNG')
            upload=client.post('/v1/inputs',headers=headers,content=buf.getvalue())
            self.assertEqual(upload.status_code,200)
            submit=client.post('/v1/batches',headers=headers,json={'jobs':[{'kind':'studio','input':upload.json()['input'],'prompt':'blue scene','brand':'makeup_house','formats':['square']}]})
            self.assertEqual(submit.status_code,200)
            batch=submit.json()['batch_id']
            job=runtime.run_next(JobHandler(root,lambda q:[],[],Editor(),Segmenter()))
            base='/v1/batches/'+batch
            row=client.get(base,headers=headers).json()['jobs'][0]
            self.assertEqual(row['state'],'COMPLETED',row)
            self.assertFalse(row['result']['publication_allowed'])
            self.assertTrue(row['result']['verification']['protected_pixels_preserved'])
            url=base+'/jobs/'+job
            self.assertEqual(client.get(url+'/export',headers=headers).status_code,200)
            response=client.get(url+'/files/square.png',headers=headers)
            self.assertEqual(response.status_code,200)
            with Image.open(io.BytesIO(response.content)) as im: self.assertEqual(im.size,(1080,1080))
            self.assertEqual(client.get(url+'/export').status_code,401)
