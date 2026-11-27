import argparse
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--backend',choices=['qwen','flux'],required=True)
    p.add_argument('--model-dir',required=True)
    a=p.parse_args()
    report={'backend':a.backend,'ready':False,'inference_verified':False}
    try:
        import torch
        import diffusers
        report['torch']=torch.__version__
        report['diffusers']=diffusers.__version__
        report['cuda_available']=torch.cuda.is_available()
        report['pipeline_available']=hasattr(diffusers,{'qwen':'QwenImageEditPlusPipeline','flux':'Flux2KleinPipeline'}[a.backend])
        report['local_model_index']=(Path(a.model_dir)/'model_index.json').is_file()
        if report['cuda_available']:
            props=torch.cuda.get_device_properties(0)
            report['gpu']=props.name
            report['vram_bytes']=props.total_memory
            report['bf16_supported']=torch.cuda.is_bf16_supported()
        report['ready']=all(report.get(k,False) for k in ('cuda_available','pipeline_available','local_model_index','bf16_supported'))
    except Exception as exc:
        report['error']=type(exc).__name__
    print(json.dumps(report,indent=2))
    if not report['ready']: raise SystemExit(1)

if __name__=='__main__': main()
