"""Run API and single worker separately with shared private data directory."""
import os
import time
import argparse
from pathlib import Path
from .batch_runtime import BatchRuntime

def main():
    p=argparse.ArgumentParser()
    p.add_argument('mode',choices=['api','worker','recover'])
    a=p.parse_args()
    root=Path(os.environ['MHVIE_DATA']).resolve()
    root.mkdir(parents=True,exist_ok=True)
    runtime=BatchRuntime(root/'jobs.sqlite3')
    if a.mode=='api':
        import uvicorn
        from .service_api import create_app
        uvicorn.run(create_app(runtime,root,os.environ['MHVIE_TOKEN']),host='127.0.0.1',port=8765)
    elif a.mode=='recover':
        print(runtime.recover_interrupted())
    else:
        from .job_handler import JobHandler
        from .search_discovery import SearxDiscovery
        editor=segmenter=None
        models={name:os.environ[key] for name,key in [('flux','MHVIE_FLUX_MODEL'),('qwen','MHVIE_QWEN_EDIT_MODEL')] if os.environ.get(key)}
        if os.environ.get('MHVIE_EDIT_MODEL'):
            models.setdefault(os.environ['MHVIE_EDIT_BACKEND'],os.environ['MHVIE_EDIT_MODEL'])
        if models:
            from .creative_studio import LocalEditor
            from .editor_router import EditorRouter
            editor=EditorRouter({name:(lambda name=name,path=path:LocalEditor(path,name)) for name,path in models.items()},os.environ.get('MHVIE_EDIT_BACKEND',next(iter(models))))
        if os.environ.get('MHVIE_SEGMENTATION')=='1':
            from .product_lock import BackgroundSegmenter
            segmenter=BackgroundSegmenter()
        evaluator=None
        if os.environ.get('MHVIE_CLIP_WEIGHTS'):
            from .visual_evaluator import LocalClip,VisualEvaluator
            from .aesthetic import AestheticPredictor
            encoder=LocalClip(os.environ['MHVIE_CLIP_WEIGHTS'],device='cpu')
            aesthetic=None
            if os.environ.get('MHVIE_AESTHETIC_WEIGHTS'):
                aesthetic=AestheticPredictor(encoder,os.environ['MHVIE_AESTHETIC_WEIGHTS'],os.environ['MHVIE_AESTHETIC_SHA256'])
            evaluator=VisualEvaluator(encoder,aesthetic)
        identity=None
        reader=None
        if os.environ.get('MHVIE_VISION_MODEL') or os.environ.get('MHVIE_OCR')=='1':
            from paddleocr import PaddleOCR
            reader=PaddleOCR(lang='en',use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False,device='cpu')
        if os.environ.get('MHVIE_VISION_MODEL'):
            from .multimodal import QwenIdentity
            from .identity_service import IdentityService
            from .safe_download import Downloader
            from .lazy_vision import LazyVision
            model=LazyVision(lambda: QwenIdentity(os.environ['MHVIE_VISION_MODEL'],max_visual_tokens=384,max_new_tokens=128))
            external=os.environ.get('MHVIE_IDENTITY_EXTERNAL_SEARCH')=='1'
            identity=IdentityService(reader,model,SearxDiscovery(os.environ['MHVIE_SEARX']) if external else None,Downloader(os.environ['MHVIE_HOSTS'].split(',')) if external else None)
        handler=JobHandler(root,SearxDiscovery(os.environ['MHVIE_SEARX']),os.environ['MHVIE_HOSTS'].split(','),editor,segmenter,evaluator,identity,reader)
        while True:
            if runtime.run_next(handler) is None: time.sleep(1)

if __name__=='__main__':
    main()
