import argparse,json,time
from pathlib import Path
from .product_lock import BackgroundSegmenter,prepare_mask
from .mask_review import preview_mask
from .creative_studio import LocalEditor
from .locked_scene import compose_scene

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--model-dir")
    p.add_argument("--reviewed-mask")
    p.add_argument("--prompt",default="Elegant beige commercial studio, soft lighting")
    a=p.parse_args()
    out=Path(a.output); out.mkdir(parents=True,exist_ok=False)
    start=time.monotonic()
    report=prepare_mask(a.source,out/"mask.png",BackgroundSegmenter())
    preview_mask(a.source,out/"mask.png",out/"preview.png")
    result={"segmentation":report,"segmentation_seconds":time.monotonic()-start,"status":"MASK_REVIEW_REQUIRED","publication_allowed":False}
    if a.reviewed_mask and a.model_dir:
        import torch
        torch.cuda.reset_peak_memory_stats()
        start=time.monotonic()
        editor=LocalEditor(a.model_dir,"flux")
        result["scene"]=compose_scene(a.source,a.reviewed_mask,editor,a.prompt,out/"edited.png",mask_reviewed=True,size=768)
        torch.cuda.synchronize()
        result.update(status="VISUAL_REVIEW_REQUIRED",generation_and_load_seconds=time.monotonic()-start,peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated())
    (out/"report.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)
if __name__=="__main__": main()
