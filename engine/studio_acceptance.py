"""Real local GPU acceptance; never treats a simulated edit as inference."""
import argparse
import hashlib
import json
import time
from pathlib import Path
from .creative_studio import LocalEditor, protected_edit
from .product_lock import BackgroundSegmenter, prepare_mask, verify_pixels

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--model-dir',required=True)
    p.add_argument('--backend',choices=['flux','qwen'],required=True)
    p.add_argument('--source',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--prompt',default='Replace only the background with an elegant ivory cosmetic photography studio, soft natural shadows and warm lighting. Preserve product position and packaging.')
    a=p.parse_args()
    import torch
    if not torch.cuda.is_available(): raise SystemExit('GPU_UNAVAILABLE')
    root=Path(a.output)
    root.mkdir(parents=True,exist_ok=False)
    report={'backend':a.backend,'inference_verified':False,'publication_allowed':False,'gpu':torch.cuda.get_device_name(0)}
    try:
        start=time.monotonic()
        segmenter=BackgroundSegmenter()
        prepare_mask(a.source,segmenter,root/'mask.png')
        report['segmentation_seconds']=time.monotonic()-start
        torch.cuda.reset_peak_memory_stats()
        start=time.monotonic()
        editor=LocalEditor(a.model_dir,a.backend)
        report['load_seconds']=time.monotonic()-start
        start=time.monotonic()
        report['edit']=protected_edit(a.source,root/'mask.png',a.prompt,editor,root/'result.png')
        torch.cuda.synchronize()
        report['edit_seconds']=time.monotonic()-start
        report['peak_cuda_bytes']=torch.cuda.max_memory_reserved()
        report['pixel_verification']=verify_pixels(a.source,root/'result.png',root/'mask.png')
        report['inference_verified']=True
        report['visual_acceptance']='HUMAN_REVIEW_REQUIRED'
        report['model_index_sha256']=hashlib.sha256((Path(a.model_dir)/'model_index.json').read_bytes()).hexdigest()
    except Exception as exc:
        report['error']=type(exc).__name__
        raise
    finally:
        (root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__':
    main()
