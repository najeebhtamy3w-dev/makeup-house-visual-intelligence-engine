"""Run one real edit with local weights; compare backends using identical inputs."""
import argparse
import json
import time
from pathlib import Path
from .creative_studio import LocalEditor,protected_edit

def main():
    p=argparse.ArgumentParser()
    for key in ('model-dir','backend','source','prompt','output'):
        p.add_argument('--'+key,required=True)
    p.add_argument('--mask')
    p.add_argument('--clip-weights')
    p.add_argument('--ocr',action='store_true')
    p.add_argument('--seed',type=int,default=42)
    a=p.parse_args()
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
