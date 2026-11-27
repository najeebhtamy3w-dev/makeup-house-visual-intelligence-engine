"""Trusted operator configuration; job payloads cannot select arbitrary paths or hosts."""
from pathlib import Path
import re
from .priority_discovery import priority_discover as discover
from .multi_input import resolve_input
from .product_registry import ProductRegistry
from .catalog_evidence import collect_catalog
from .safe_download import Downloader
from .photo_workflow import photo_discovery,read_barcodes
from .campaign_formats import render_formats
from .creative_studio import protected_edit
from .locked_scene import compose_scene
from .mask_review import correct_mask,preview_mask
from .brand_profiles import campaign_prompt
from .review_export import export_review
from .product_lock import prepare_mask,verify_pixels

class JobHandler:
    def __init__(self,root,search,hosts,editor=None,segmenter=None,visual_evaluator=None,identity_service=None,ocr_reader=None):
        self.identity_service=identity_service
        self.ocr_reader=ocr_reader
        self.root=Path(root).resolve()
        self.search=search
        self.root.mkdir(parents=True,exist_ok=True)
        self.registry=ProductRegistry(self.root/'products.sqlite3')
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
        elif kind=='barcode':
            result={'barcodes':read_barcodes(self.input(payload['input'])),'identity_verified':False}
        elif kind=='smart_discover':
            path=self.input(payload['input']) if payload.get('input') else None
            def lookup(code):
                local=self.registry.lookup(code)
                if local: return local
                return collect_catalog(list(self.search(code))[:3],Downloader(self.hosts))['evidence']
            def visual(path):
                if self.identity_service is None: raise RuntimeError('IDENTITY_UNAVAILABLE')
                return photo_discovery(path,self.identity_service,self.search,self.hosts,output,self.visual_evaluator,payload.get('purpose','catalog'),ocr_reader=self.ocr_reader)
            def named(query):
                return discover(query[:240],self.search,self.hosts,output,visual_evaluator=self.visual_evaluator,purpose=payload.get('purpose','catalog'))
            result=resolve_input(payload.get('barcode'),payload.get('query'),path,lookup,visual,named,barcode_reader=read_barcodes)
        elif kind=='photo_discover':
            if self.identity_service is None: raise RuntimeError('IDENTITY_UNAVAILABLE')
            result=photo_discovery(self.input(payload['input']),self.identity_service,self.search,self.hosts,output,self.visual_evaluator,payload.get('purpose','catalog'),ocr_reader=self.ocr_reader)
        elif kind=='identify':
            if self.identity_service is None: raise RuntimeError('IDENTITY_UNAVAILABLE')
            result=self.identity_service(self.input(payload['input']))
        elif kind=='prepare_mask':
            if self.segmenter is None: raise RuntimeError('SEGMENTER_UNAVAILABLE')
            result=prepare_mask(self.input(payload['input']),output/'mask.png',self.segmenter)
            preview_mask(self.input(payload['input']),output/'mask.png',output/'preview.png')
        elif kind=='correct_mask':
            result=correct_mask(self.input(payload['input']),self.input(payload['mask_input']),output/'mask.png',payload['strokes'])
        elif kind=='locked_scene':
            if self.editor is None: raise RuntimeError('STUDIO_UNAVAILABLE')
            if payload.get('mask_reviewed') is not True: raise ValueError('HUMAN_MASK_REVIEW_REQUIRED')
            source=self.input(payload['input'])
            mask=self.input(payload['mask_input'])
            prompt=campaign_prompt(payload['brand'],payload['prompt']) if payload.get('brand') else payload['prompt']
            result=compose_scene(source,mask,self.editor,prompt,output/'edited.png',mask_reviewed=True)
            result['formats']=render_formats(output/'edited.png',output,payload.get('formats') or [])
            result['formats_require_review']=True
            result['text_qa']={'status':'OCR_NOT_CONFIGURED','identity_verified':False}
            if self.ocr_reader is not None:
                from .scene_text_qa import compare_text
                from .identity_fusion import read_ocr,strong_lines
                import tempfile
                def read_crop(image):
                    with tempfile.TemporaryDirectory() as d:
                        path=Path(d)/'crop.png'
                        image.save(path)
                        return strong_lines(read_ocr(path,self.ocr_reader))
                try:
                    result['text_qa']=compare_text(source,output/'edited.png',result['placement'],result['source_bounds'],read_crop)
                except Exception as exc:
                    result['text_qa']={'status':'OCR_FAILED','error':type(exc).__name__,'identity_verified':False}
        elif kind=='direct_edit':
            if self.editor is None: raise RuntimeError('STUDIO_UNAVAILABLE')
            from PIL import Image,ImageOps
            import hashlib
            source=self.input(payload['input'])
            with Image.open(source) as im:
                if im.width*im.height>25000000: raise ValueError('PIXEL_LIMIT')
                original=ImageOps.exif_transpose(im).convert('RGB')
            prompt=campaign_prompt(payload['brand'],payload['prompt']) if payload.get('brand') else payload['prompt']
            edited=self.editor.edit(original,prompt,42).convert('RGB')
            with (output/'edited.png').open('xb') as f: edited.save(f,format='PNG')
            from .direct_edit_qa import assess_edit
            qa=assess_edit(source,output/'edited.png',self.visual_evaluator,self.ocr_reader)
            result={'quality_review':qa,'status':'VISUAL_REVIEW_REQUIRED','identity_verified':False,'protected_pixels_preserved':None,'mask_required':False,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
            result['formats']=render_formats(output/'edited.png',output,payload.get('formats') or [])
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
            result['formats']=render_formats(output/'edited.png',output,payload.get('formats') or [])
        else: raise ValueError('UNKNOWN_JOB_KIND')
        result['artifact_directory']=str(output.relative_to(self.root))
        result['publication_allowed']=False
        result['brand']=payload.get('brand')
        if kind in ('direct_edit','locked_scene','studio','discover','photo_discover','smart_discover'):
            archive=output.parent/(output.name+'.zip')
            export_review(output,archive,result)
            result['review_archive']=archive.name
        return result
