"""Run both configured local editors in separate processes; no implicit downloads."""
import argparse,json,subprocess,sys
from pathlib import Path
from .studio_benchmark import dataset

def main():
    p=argparse.ArgumentParser()
    for key in ('photos','flux','qwen','output'):
        p.add_argument('--'+key,required=True)
    p.add_argument('--clip-weights')
    p.add_argument('--ocr',action='store_true')
    p.add_argument('--manifest',required=True)
    a=p.parse_args()
    photos=dataset(a.photos,a.manifest)
    root=Path(a.output)
    root.mkdir(parents=True,exist_ok=True)
    reports=[]
    prompt='Create a premium cosmetic advertising photograph with elegant lighting and a clean background. Preserve the exact package, logo, printed text, color and shape.'
    for backend in ('flux','qwen'):
        output=root/backend
        cmd=[sys.executable,'-m','engine.studio_benchmark','--backend',backend,'--model-dir',getattr(a,backend),'--photos',a.photos,'--manifest',a.manifest,'--output',str(output),'--prompt',prompt,'--seed','42']
        if a.clip_weights: cmd+=['--clip-weights',a.clip_weights]
        if a.ocr: cmd+=['--ocr']
        try:
            completed=subprocess.run(cmd,check=False,timeout=18000)
            rows=json.loads((output/'group.json').read_text())['results']
            if len(rows)!=10: raise ValueError('INCOMPLETE_GROUP')
            for row,(name,_,digest) in zip(rows,photos):
                if row.get('image_id')!=name or row.get('source_sha256')!=digest or row.get('backend')!=backend or row.get('seed')!=42 or row.get('prompt')!=prompt:
                    raise ValueError('GROUP_EVIDENCE_MISMATCH')
            if completed.returncode and all(r['status']=='REVIEW_REQUIRED' for r in rows): raise ValueError('CHILD_FAILED')
            reports.extend(rows)
        except (subprocess.SubprocessError,OSError,ValueError,KeyError) as exc:
            reports.extend({'backend':backend,'image_id':name,'source_sha256':digest,'status':'BLOCKED','error':type(exc).__name__,'publication_allowed':False} for name,_,digest in photos)
        (root/'comparison.json').write_text(json.dumps(reports,indent=2,allow_nan=False))
    if any(r.get('status')!='REVIEW_REQUIRED' for r in reports): raise SystemExit('GPU_BENCHMARK_INCOMPLETE')
if __name__=='__main__': main()
