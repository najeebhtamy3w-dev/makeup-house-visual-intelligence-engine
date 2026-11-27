"""Measure actual local inference; no accuracy or speed claims without evidence."""
import argparse
import json
import time
import resource
import hashlib
from pathlib import Path
from PIL import Image, ImageOps
from .multimodal import QwenIdentity

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--model-dir',required=True)
    p.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    p.add_argument('--visual-tokens',type=int,choices=[256,384,768,1024],default=384)
    p.add_argument('--output',required=True)
    p.add_argument('images',nargs='+')
    a=p.parse_args()
    import torch
    start=time.monotonic()
    model=QwenIdentity(a.model_dir,device=a.device,max_visual_tokens=a.visual_tokens,max_new_tokens=128)
    report={'device':a.device,'visual_tokens':a.visual_tokens,'load_seconds':time.monotonic()-start,'torch':torch.__version__,'accuracy_verified':False,'rows':[]}
    for path in a.images:
        with Image.open(path) as im:
            if im.width*im.height>25000000: raise ValueError('PIXEL_LIMIT')
            image=ImageOps.exif_transpose(im).convert('RGB')
        for run in range(2):
            start=time.monotonic()
            row={'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'repeat':run}
            try:
                row['result']=model.identify(image)
            except Exception as exc:
                row['error']=type(exc).__name__
            if a.device=='cuda': torch.cuda.synchronize()
            row['seconds']=time.monotonic()-start
            report['rows'].append(row)
            print(json.dumps(row,ensure_ascii=False),flush=True)
    report['peak_rss_kib_linux']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if a.device=='cuda': report['peak_cuda_bytes']=torch.cuda.max_memory_allocated()
    with open(a.output,'x',encoding='utf-8') as f: json.dump(report,f,ensure_ascii=False,indent=2)
    if any('error' in row or not row['result'].get('fields') for row in report['rows']): raise SystemExit(1)

if __name__=='__main__': main()
