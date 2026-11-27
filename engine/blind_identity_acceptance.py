import argparse, hashlib, json, time
from pathlib import Path
from PIL import Image
from .multimodal import QwenIdentity

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',required=True)
    p.add_argument('--model',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    manifest=Path(a.manifest).resolve()
    rows=json.loads(manifest.read_text())
    if not isinstance(rows,list) or not 1<=len(rows)<=100:
        raise ValueError('INVALID_MANIFEST')
    model=QwenIdentity(a.model)
    output=Path(a.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    results=[]
    for i,row in enumerate(rows,1):
        start=time.monotonic()
        try:
            if row.get('name') or row.get('fields') or row.get('seeds'):
                raise ValueError('LABEL_LEAKAGE')
            path=(manifest.parent/row['image']).resolve()
            if not path.is_relative_to(manifest.parent): raise ValueError('INVALID_PATH')
            if path.stat().st_size>10000000: raise ValueError('SIZE_LIMIT')
            if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']: raise ValueError('HASH_MISMATCH')
            with Image.open(path) as im:
                if im.width*im.height>25000000: raise ValueError('PIXEL_LIMIT')
                result=model.identify(im.convert('RGB'))
        except Exception as exc:
            result={'status':'FAILED','error':str(exc)}
        results.append(dict(index=i,elapsed_seconds=time.monotonic()-start,**result))
        output.write_text(json.dumps({'human_validation':'PENDING','results':results},ensure_ascii=False,indent=2),encoding='utf-8')
    if any(x['status']=='FAILED' or not x.get('fields') for x in results):
        raise SystemExit('IDENTITY_GATE_FAILED')
if __name__=='__main__': main()
