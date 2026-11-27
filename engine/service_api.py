"""Private backend API. Deploy behind TLS; one trusted worker per queue."""
import hashlib
import hmac
import json
import io
import re
import os
import tempfile
from fastapi.responses import FileResponse
from pathlib import Path
from PIL import Image
from fastapi import FastAPI, HTTPException, Header, Request, Depends
from pydantic import BaseModel, Field
from typing import Literal
from .barcode_priority import canonical_gtin

class Stroke(BaseModel):
    mode: Literal['erase','restore']
    radius: int=Field(ge=1,le=256)
    points: list[tuple[int,int]]=Field(min_length=1,max_length=256)

class Job(BaseModel):
    kind: Literal['discover','studio','identify','barcode','photo_discover','smart_discover','prepare_mask','locked_scene','correct_mask','direct_edit']
    formats: list[Literal['square','story','portrait']]=Field(default_factory=list,max_length=3)
    brand: Literal['makeup_house','unwan_al_atr']|None=None
    barcode: str|None=Field(default=None,max_length=14)
    query: str|None=Field(default=None,max_length=240)
    purpose: Literal['catalog','marketing']='catalog'
    input: str|None=Field(default=None,max_length=70)
    mask_input: str|None=Field(default=None,max_length=70)
    mask_reviewed: bool=False
    strokes: list[Stroke]=Field(default_factory=list,max_length=100)
    prompt: str|None=Field(default=None,max_length=1500)

class Batch(BaseModel):
    jobs: list[Job]=Field(min_length=1,max_length=100)

def create_app(runtime,root,token):
    if len(token)<32: raise ValueError('STRONG_TOKEN_REQUIRED')
    root=Path(root)
    app=FastAPI(title='MH-VIE Core',version='0.24',docs_url=None,redoc_url=None,openapi_url=None)
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
            if len(data)+len(chunk)>10000000: raise HTTPException(413,'INPUT_LIMIT')
            data.extend(chunk)
        try:
            with Image.open(io.BytesIO(data)) as im:
                ext={'PNG':'png','JPEG':'jpg','WEBP':'webp'}.get(im.format)
                if not ext or im.width*im.height>25000000: raise ValueError()
                im.verify()
        except Exception: raise HTTPException(422,'INVALID_IMAGE')
        name=hashlib.sha256(data).hexdigest()+'.'+ext
        folder=root/'inputs'; folder.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=folder,delete=False) as f:
            temp=Path(f.name)
            try:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
                f.close()
                try: os.link(temp,folder/name)
                except FileExistsError:
                    if (folder/name).is_symlink() or not (folder/name).is_file() or hashlib.sha256((folder/name).read_bytes()).hexdigest()!=name.split('.')[0]:
                        raise HTTPException(409,'INPUT_INTEGRITY_CONFLICT')
            finally:
                temp.unlink(missing_ok=True)
        return {'input':name}
    @app.post('/v1/batches',dependencies=[Depends(auth)])
    def submit(batch:Batch):
        for job in batch.jobs:
            if job.input is not None:
                if not re.fullmatch(r'[a-f0-9]{64}\.(png|jpg|jpeg|webp)',job.input): raise HTTPException(422,'INVALID_INPUT_ID')
                candidate=root/'inputs'/job.input
                if candidate.is_symlink() or not candidate.is_file(): raise HTTPException(404,'INPUT_NOT_FOUND')
            if job.kind=='correct_mask' and not (job.input and job.mask_input and job.strokes): raise HTTPException(422,'MASK_CORRECTION_INPUT_REQUIRED')
            if job.kind in ('locked_scene','correct_mask'):
                if job.kind=='locked_scene' and not (job.input and job.mask_input and job.mask_reviewed and (job.prompt or '').strip()):
                    raise HTTPException(422,'REVIEWED_MASK_AND_PROMPT_REQUIRED')
                if not re.fullmatch(r'[a-f0-9]{64}\.png',job.mask_input): raise HTTPException(422,'INVALID_MASK_ID')
                mask=root/'inputs'/job.mask_input
                if mask.is_symlink() or not mask.is_file(): raise HTTPException(404,'MASK_NOT_FOUND')
            if job.kind=='smart_discover':
                if job.barcode is not None and canonical_gtin(job.barcode) is None: raise HTTPException(422,'INVALID_GTIN')
                if not (job.barcode or job.input or (job.query or '').strip()): raise HTTPException(422,'ADDITIONAL_INPUT_REQUIRED')
            if job.kind=='discover' and not (job.query or '').strip(): raise HTTPException(422,'QUERY_REQUIRED')
            if job.kind in ('identify','barcode','photo_discover','prepare_mask') and not job.input: raise HTTPException(422,'INPUT_REQUIRED')
            if job.kind in ('studio','direct_edit') and not (job.input and (job.prompt or '').strip()): raise HTTPException(422,'STUDIO_INPUT_REQUIRED')
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
        if not re.fullmatch(r'(?:[a-f0-9]{64}\.bin|edited\.png|mask\.png|preview\.png|square\.png|story\.png|portrait\.png)',name):
            raise HTTPException(404,'FILE_NOT_FOUND')
        row=next((r for r in runtime.status(batch_id) if r['id']==job_id and r['state']=='COMPLETED'),None)
        if row is None: raise HTTPException(404,'JOB_NOT_FOUND')
        result=json.loads(row['result'])
        directory=result.get('artifact_directory')
        if not isinstance(directory,str): raise HTTPException(404,'FILE_NOT_FOUND')
        base=(root/directory).resolve()
        expected=(root/'jobs'/job_id).resolve()
        file=(base/name).resolve()
        if base.parent!=expected or file.parent!=base or not file.is_file():
            raise HTTPException(404,'FILE_NOT_FOUND')
        return FileResponse(file,media_type='application/octet-stream',filename=name)
    @app.get('/v1/batches/{batch_id}/jobs/{job_id}/export',dependencies=[Depends(auth)])
    def export(batch_id:str,job_id:str):
        row=next((r for r in runtime.status(batch_id) if r['id']==job_id and r['state']=='COMPLETED'),None)
        if row is None: raise HTTPException(404,'JOB_NOT_FOUND')
        result=json.loads(row['result'])
        name=result.get('review_archive','')
        if not re.fullmatch(r'[a-f0-9]{32}\.zip',name): raise HTTPException(404,'EXPORT_NOT_FOUND')
        base=(root/'jobs'/job_id).resolve()
        file=(base/name).resolve()
        if file.parent!=base or not file.is_file(): raise HTTPException(404,'EXPORT_NOT_FOUND')
        return FileResponse(file,media_type='application/zip',filename='review.zip')
    return app
