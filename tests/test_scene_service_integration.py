import tempfile,io,unittest
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient
from engine.service_api import create_app
from engine.batch_runtime import BatchRuntime
from engine.job_handler import JobHandler

class Segmenter:
    def segment(self,image):
        m=Image.new("L",image.size)
        m.paste(255,(20,20,80,80))
        return m
class Editor:
    def background(self,prompt,width,height,seed):
        return Image.new("RGB",(width,height),"gold")

class SceneServiceTests(unittest.TestCase):
    def test_workflow(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            runtime=BatchRuntime(root/"jobs.sqlite3")
            client=TestClient(create_app(runtime,root,"x"*32))
            client.headers["Authorization"]="Bearer "+"x"*32
            handler=JobHandler(root,lambda q:[],(),Editor(),Segmenter())
            buf=io.BytesIO()
            Image.new("RGB",(100,100),"blue").save(buf,format="PNG")
            def upload(data):
                response=client.post("/v1/inputs",content=data)
                self.assertEqual(response.status_code,200,response.text)
                return response.json()["input"]
            def run(payload):
                response=client.post("/v1/batches",json={"jobs":[payload]})
                self.assertEqual(response.status_code,200,response.text)
                batch=response.json()["batch_id"]
                runtime.run_next(handler)
                row=client.get("/v1/batches/"+batch).json()["jobs"][0]
                self.assertEqual(row["state"],"COMPLETED",str(row))
                return batch,row
            source=upload(buf.getvalue())
            batch,row=run({"kind":"prepare_mask","input":source})
            base=f"/v1/batches/{batch}/jobs/{row['id']}/files/"
            preview=client.get(base+"preview.png")
            self.assertEqual(preview.status_code,200)
            mask=upload(client.get(base+"mask.png").content)
            batch,row=run({"kind":"correct_mask","input":source,"mask_input":mask,"strokes":[{"mode":"erase","radius":2,"points":[[21,21]]}]})
            mask=upload(client.get(f"/v1/batches/{batch}/jobs/{row['id']}/files/mask.png").content)
            payload={"kind":"locked_scene","input":source,"mask_input":mask,"prompt":"marble"}
            self.assertEqual(client.post("/v1/batches",json={"jobs":[payload]}).status_code,422)
            payload["mask_reviewed"]=True
            batch,row=run(payload)
            self.assertTrue(row["result"]["protected_pixels_preserved"])
            self.assertFalse(row["result"]["publication_allowed"])
            self.assertEqual(client.get(f"/v1/batches/{batch}/jobs/{row['id']}/export").status_code,200)
