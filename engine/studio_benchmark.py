"""Run one real edit with local weights; compare backends using identical inputs."""
import argparse
import json
import time
import hashlib
from pathlib import Path
from .creative_studio import LocalEditor,protected_edit

def dataset(photos,manifest):
    root=Path(photos).resolve()
    rows=json.loads(Path(manifest).read_text())
    if not isinstance(rows,list) or len(rows)!=10: raise ValueError('EXACTLY_TEN_REFERENCE_PHOTOS_REQUIRED')
    result=[];seen=set()
    for row in rows:
        name=row.get('image')
        if not isinstance(name,str): raise ValueError('INVALID_DATASET_PATH')
        path=(root/name).resolve()
        if not path.is_relative_to(root) or path.is_symlink() or not path.is_file() or path.stat().st_size>10000000:
            raise ValueError('INVALID_DATASET_PATH')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=row.get('sha256') or digest in seen: raise ValueError('DATASET_HASH_MISMATCH')
        seen.add(digest);result.append((name,path,digest))
    return result

def run_group(photos,manifest,model_dir,backend,output,prompt,seed=42,editor_factory=None,evaluator=None,reader=None):
    """One model lifetime per group. Injected factories are synthetic test seams."""
    from PIL import Image,ImageOps
    from .direct_edit_qa import assess_edit
    rows=dataset(photos,manifest)
    target=Path(output);target.mkdir(parents=True,exist_ok=True)
    reports=[];editor=None;error=None;load_seconds=None
    started=time.monotonic()
    try:
        if not Path(model_dir).is_dir(): raise FileNotFoundError('LOCAL_MODEL_REQUIRED')
        editor=(editor_factory or LocalEditor)(model_dir,backend)
        load_seconds=time.monotonic()-started
    except Exception as exc:
        error=type(exc).__name__+':'+str(exc)[:160]
    for i,(name,path,digest) in enumerate(rows):
        row={'image_id':name,'source_sha256':digest,'backend':backend,'seed':seed,'prompt':prompt,
             'status':'BLOCKED','identity_verified':False,'publication_allowed':False,'quality_accepted':False}
        if error: row['error']=error
        else:
            try:
                start=time.monotonic()
                with Image.open(path) as image:
                    if image.width*image.height>25000000: raise ValueError('PIXEL_LIMIT')
                    original=ImageOps.exif_transpose(image).convert('RGB')
                result=editor.edit(original,prompt,seed).convert('RGB')
                if result.width*result.height>25000000: raise ValueError('PIXEL_LIMIT')
                file=target/f'{i+1:02}.png'
                with file.open('xb') as stream: result.save(stream,format='PNG')
                row.update(status='REVIEW_REQUIRED',output=file.name,output_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                           inference_seconds=time.monotonic()-start,quality_review=assess_edit(path,file,evaluator,reader),
                           real_inference_verified=editor_factory is None)
            except Exception as exc:
                row.update(status='FAILED',error=type(exc).__name__+':'+str(exc)[:160])
        reports.append(row)
        (target/'group.json').write_text(json.dumps({'backend':backend,'model_load_count':int(editor is not None),
            'load_seconds':load_seconds,'test_adapter':editor_factory is not None,'results':reports},indent=2,allow_nan=False))
    return reports

def main():
    p=argparse.ArgumentParser()
    for key in ('model-dir','backend','prompt','output'):
        p.add_argument('--'+key,required=True)
    inputs=p.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--source')
    inputs.add_argument('--photos')
    p.add_argument('--manifest')
    p.add_argument('--mask')
    p.add_argument('--clip-weights')
    p.add_argument('--ocr',action='store_true')
    p.add_argument('--seed',type=int,default=42)
    a=p.parse_args()
    if a.photos:
        if not a.manifest: p.error('--manifest is required with --photos')
        evaluator=reader=None
        # Review models, when configured, are initialized once for this group.
        if Path(a.model_dir).is_dir():
            if a.clip_weights:
                from .visual_evaluator import LocalClip,VisualEvaluator
                evaluator=VisualEvaluator(LocalClip(a.clip_weights,device='cpu'))
            if a.ocr:
                from paddleocr import PaddleOCR
                reader=PaddleOCR(lang='en',use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False,device='cpu')
        rows=run_group(a.photos,a.manifest,a.model_dir,a.backend,a.output,a.prompt,a.seed,evaluator=evaluator,reader=reader)
        if any(r['status']!='REVIEW_REQUIRED' for r in rows): raise SystemExit(2)
        return
    import torch
    if not torch.cuda.is_available(): raise SystemExit('GPU_UNAVAILABLE')
    torch.cuda.reset_peak_memory_stats()
    start=time.monotonic()
    editor=LocalEditor(a.model_dir,a.backend)
    load=time.monotonic()-start
    start=time.monotonic()
    if a.mask:
        report=protected_edit(a.source,a.mask,a.prompt,editor,a.output,a.seed)
    else:
        from PIL import Image,ImageOps
        import hashlib
        with Image.open(a.source) as im:
            if im.width*im.height>25000000: raise ValueError('PIXEL_LIMIT')
            original=ImageOps.exif_transpose(im).convert('RGB')
        edited=editor.edit(original,a.prompt,a.seed).convert('RGB')
        with Path(a.output).open('xb') as stream: edited.save(stream,format='PNG')
        report={'status':'REVIEW_REQUIRED','identity_verified':False,'publication_allowed':False,'source_sha256':hashlib.sha256(Path(a.source).read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(Path(a.output).read_bytes()).hexdigest(),'seed':a.seed}
    report['mode']='protected' if a.mask else 'direct'
    report['prompt']=a.prompt
    torch.cuda.synchronize()
    report.update(backend=a.backend,gpu=torch.cuda.get_device_name(),load_seconds=load,edit_seconds=time.monotonic()-start,peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved())
    from .direct_edit_qa import assess_edit
    evaluator=reader=None
    if a.clip_weights:
        from .visual_evaluator import LocalClip,VisualEvaluator
        evaluator=VisualEvaluator(LocalClip(a.clip_weights,device='cpu'))
    if a.ocr:
        from paddleocr import PaddleOCR
        reader=PaddleOCR(lang='en',use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False,device='cpu')
    report['quality_review']=assess_edit(a.source,a.output,evaluator,reader)
    Path(a.output+'.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    main()
