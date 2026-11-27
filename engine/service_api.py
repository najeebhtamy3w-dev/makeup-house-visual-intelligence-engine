"""Private backend API. Deploy behind TLS; one trusted worker per queue."""
import hashlib
import hmac
import json
import io
import re
from fastapi.responses import FileResponse
from pathlib import Path
from PIL import Image
from fastapi import FastAPI, HTTPException, Header, Request, Depends
from pydantic import BaseModel, Field
from typing import Literal

class Job(BaseModel):
    kind: Literal['discover','studio']
    query: str|None=Field(default=None,max_length=240)
    purpose: Literal['catalog','marketing']='catalog'
    input: str|None=Field(default=None,max_length=70)
    prompt: str|None=Field(default=None,max_length=2000)

class Batch(BaseModel):
    jobs: list[Job]=Field(min_length=1,max_length=100)

def create_app(runtime,root,token):
    if len(token)<32: raise ValueError('STRONG_TOKEN_REQUIRED')
    root=Path(root)
    app=FastAPI(title='MH-VIE Core',version='0.22',docs_url=None,redoc_url=None,openapi_url=None)
    def auth(authorization: str=Header(default='')):
        if not hmac.compare_digest(authorization.encode(),('Bearer '+token).encode()):
            raise HTTPException(401,'UNAUTHORIZED')
    @app.get('/v1/health',dependencies=[Depends(auth)])
    def health():
        return {'status':'API_AVAILABLE','model_readiness':'NOT_VERIFIED'}
    @app.post('/v1/inputs',dependencies=[Depends(auth)])
    async def upload(request:Request):
        data=bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data)>10000000: raise HTTPException(413,'INPUT_LIMIT')
        try:
            with Image.open(io.BytesIO(data)) as im:
                ext={'PNG':'png','JPEG':'jpg','WEBP':'webp'}.get(im.format)
                if not ext or im.width*im.height>25000000: raise ValueError()
                im.verify()
        except Exception: raise HTTPException(422,'INVALID_IMAGE')
        name=hashlib.sha256(data).hexdigest()+'.'+ext
        folder=root/'inputs'; folder.mkdir(parents=True,exist_ok=True)
        try:
            with (folder/name).open('xb') as f: f.write(data)
        except FileExistsError: pass
        return {'input':name}
    @app.post('/v1/batches',dependencies=[Depends(auth)])
    def submit(batch:Batch):
        for job in batch.jobs:
            if job.kind=='discover' and not (job.query or '').strip(): raise HTTPException(422,'QUERY_REQUIRED')
            if job.kind=='studio' and not (job.input and (job.prompt or '').strip()): raise HTTPException(422,'STUDIO_INPUT_REQUIRED')
        return {'batch_id':runtime.submit([j.model_dump() for j in batch.jobs])}
    @app.get('/v1/batches/{batch_id}',dependencies=[Depends(auth)])
    def status(batch_id:str):
        rows=runtime.status(batch_id)
        if not rows: raise HTTPException(404,'BATCH_NOT_FOUND')
        for row in rows:
            for key in ('payload','result'):
                if row[key] is not None: row[key]=json.loads(row[key])
        return {'batch_id':batch_id,'jobs':rows}
    @app.post('/v1/batches/{batch_id}/retry',dependencies=[Depends(auth)])
    def retry(batch_id:str):
        if not runtime.status(batch_id): raise HTTPException(404,'BATCH_NOT_FOUND')
        return {'requeued':runtime.retry(batch_id)}
    @app.get('/v1/batches/{batch_id}/jobs/{job_id}/files/{name}',dependencies=[Depends(auth)])
    def artifact(batch_id:str,job_id:str,name:str):
        if not re.fullmatch(r'(?:[a-f0-9]{64}\.bin|edited\.png|mask\.png)',name):
            raise HTTPException(404,'FILE_NOT_FOUND')
        row=next((r for r in runtime.status(batch_id) if r['id']==job_id and r['state']=='COMPLETED'),None)
        if row is None: raise HTTPException(404,'JOB_NOT_FOUND')
        result=json.loads(row['result'])
        base=(root/result['artifact_directory']).resolve()
        expected=(root/'jobs'/job_id).resolve()
        file=(base/name).resolve()
        if base.parent!=expected or file.parent!=base or not file.is_file():
            raise HTTPException(404,'FILE_NOT_FOUND')
        return FileResponse(file,media_type='application/octet-stream',filename=name)
    return app
