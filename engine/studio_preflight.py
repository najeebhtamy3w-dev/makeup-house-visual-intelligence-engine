"""Check the actual LocalEditor GPU profile without loading model weights."""
import argparse
import json
from pathlib import Path


def assess(backend,model_dir):
    if backend not in ('qwen','flux'):
        raise ValueError('UNKNOWN_BACKEND')
    report={'backend':backend,'ready':False,'inference_verified':False,
            'ready_scope':'STATIC_PREREQUISITES_ONLY','blockers':[]}
    try:
        import torch
        import diffusers
        report['torch']=torch.__version__
        report['diffusers']=diffusers.__version__
        report['cuda_available']=torch.cuda.is_available()
        report['pipeline_available']=hasattr(diffusers,{'qwen':'QwenImageEditPlusPipeline','flux':'Flux2KleinPipeline'}[backend])
        report['local_model_index']=(Path(model_dir)/'model_index.json').is_file()
        if not report['cuda_available']:
            report['blockers'].append('GPU_UNAVAILABLE')
        if not report['pipeline_available']:
            report['blockers'].append('PIPELINE_UNAVAILABLE')
        if not report['local_model_index']:
            report['blockers'].append('LOCAL_MODEL_INDEX_REQUIRED')
        if report['cuda_available']:
            props=torch.cuda.get_device_properties(0)
            report['gpu']=props.name
            report['vram_bytes']=props.total_memory
            report['compute_capability']=list(torch.cuda.get_device_capability())
            report['bf16_supported']=torch.cuda.is_bf16_supported()
            # Match LocalEditor: Qwen's tested profile needs native Ampere BF16;
            # FLUX explicitly supports the pre-Ampere FP16 profile (e.g. T4).
            native_bf16=report['compute_capability'][0]>=8
            report['native_bf16']=native_bf16
            report['selected_dtype']='bfloat16' if native_bf16 else 'float16'
            if backend=='qwen' and not native_bf16:
                report['blockers'].append('NATIVE_BF16_REQUIRED_FOR_QWEN_PROFILE')
        report['ready']=not report['blockers']
    except Exception as exc:
        report['error']=type(exc).__name__
        report['blockers'].append('PREFLIGHT_FAILED:'+type(exc).__name__)
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--backend',choices=['qwen','flux'],required=True)
    p.add_argument('--model-dir',required=True)
    args=p.parse_args()
    report=assess(args.backend,args.model_dir)
    print(json.dumps(report,indent=2))
    if not report['ready']: raise SystemExit(1)


if __name__=='__main__': main()
