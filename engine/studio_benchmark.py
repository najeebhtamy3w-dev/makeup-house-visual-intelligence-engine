"""Run one real edit with local weights; compare backends using identical inputs."""
import argparse
import json
import time
from pathlib import Path
from .creative_studio import LocalEditor,protected_edit

def main():
    p=argparse.ArgumentParser()
    for key in ('model-dir','backend','source','mask','prompt','output'):
        p.add_argument('--'+key,required=True)
    p.add_argument('--seed',type=int,default=42)
    a=p.parse_args()
    import torch
    if not torch.cuda.is_available(): raise SystemExit('GPU_UNAVAILABLE')
    torch.cuda.reset_peak_memory_stats()
    start=time.monotonic()
    editor=LocalEditor(a.model_dir,a.backend)
    load=time.monotonic()-start
    start=time.monotonic()
    report=protected_edit(a.source,a.mask,a.prompt,editor,a.output,a.seed)
    torch.cuda.synchronize()
    report.update(backend=a.backend,gpu=torch.cuda.get_device_name(),load_seconds=load,edit_seconds=time.monotonic()-start,peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved())
    Path(a.output+'.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    main()
