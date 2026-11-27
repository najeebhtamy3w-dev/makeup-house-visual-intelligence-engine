"""Trusted operator configuration; job payloads cannot select arbitrary paths or hosts."""
from pathlib import Path
import re
from .integration_core import discover
from .creative_studio import protected_edit
from .brand_profiles import campaign_prompt
from .review_export import export_review
from .product_lock import prepare_mask,verify_pixels

class JobHandler:
    def __init__(self,root,search,hosts,editor=None,segmenter=None,visual_evaluator=None,identity_service=None):
        self.identity_service=identity_service
        self.root=Path(root).resolve()
        self.search=search
        self.hosts=tuple(hosts)
        self.editor=editor
        self.segmenter=segmenter
        self.visual_evaluator=visual_evaluator
    def input(self,name):
        if not isinstance(name,str) or not re.fullmatch(r'[a-f0-9]{64}\.(png|jpg|jpeg|webp)',name):
            raise ValueError('INVALID_INPUT_ID')
        path=(self.root/'inputs'/name).resolve()
        if path.parent!=(self.root/'inputs').resolve() or not path.is_file(): raise ValueError('INPUT_NOT_FOUND')
        return path
    def __call__(self,job,payload):
        if not re.fullmatch(r'[a-f0-9]{32}',job): raise ValueError('INVALID_JOB_ID')
        import uuid
        output=self.root/'jobs'/job/uuid.uuid4().hex
        output.mkdir(parents=True,exist_ok=False)
        kind=payload.get('kind')
        if kind=='discover':
            result=discover(payload['query'],self.search,self.hosts,output,visual_evaluator=self.visual_evaluator,purpose=payload.get('purpose','catalog'))
        elif kind=='identify':
            if self.identity_service is None: raise RuntimeError('IDENTITY_UNAVAILABLE')
            result=self.identity_service(self.input(payload['input']))
        elif kind=='studio':
            if self.editor is None or self.segmenter is None: raise RuntimeError('STUDIO_UNAVAILABLE')
            source=self.input(payload['input'])
            mask=output/'mask.png'
            mask_report=prepare_mask(source,mask,self.segmenter)
            prompt=campaign_prompt(payload['brand'],payload['prompt']) if payload.get('brand') else payload['prompt']
            result=protected_edit(source,mask,prompt,self.editor,output/'edited.png')
            result['mask']=mask_report
            result['verification']=verify_pixels(source,output/'edited.png',mask)
            if not result['verification']['protected_pixels_preserved']: raise RuntimeError('IDENTITY_LOCK_FAILED')
        else: raise ValueError('UNKNOWN_JOB_KIND')
        result['artifact_directory']=str(output.relative_to(self.root))
        result['publication_allowed']=False
        result['brand']=payload.get('brand')
        if kind in ('studio','discover'):
            archive=output.parent/(output.name+'.zip')
            export_review(output,archive,result)
            result['review_archive']=archive.name
        return result
