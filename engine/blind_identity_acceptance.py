import argparse, hashlib, json, time
from pathlib import Path
from PIL import Image
from .multimodal import QwenIdentity

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',required=True)
    p.add_argument('--model',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--index',type=int)
    p.add_argument('--visual-tokens',type=int,default=384)
    p.add_argument('--new-tokens',type=int,default=128)
    p.add_argument('--ocr',action='store_true')
    a=p.parse_args()
    manifest=Path(a.manifest).resolve()
    rows=json.loads(manifest.read_text())
    if not isinstance(rows,list) or not 1<=len(rows)<=100:
        raise ValueError('INVALID_MANIFEST')
    if a.index is not None and not 1<=a.index<=len(rows): raise ValueError('INVALID_INDEX')
    model=None
    def visual(image):
        nonlocal model
        if model is None:
            print('Loading model',flush=True)
            model=QwenIdentity(a.model,max_visual_tokens=a.visual_tokens,max_new_tokens=a.new_tokens)
            print('Model loaded',flush=True)
        return model.identify(image)
    reader=None
    if a.ocr:
        from paddleocr import PaddleOCR
        from .identity_fusion import fuse, read_ocr
        reader=PaddleOCR(lang='en',use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False,device='cpu')
    output=Path(a.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    results=[]
    for i,row in enumerate(rows,1):
        if a.index is not None and i!=a.index: continue
        print(f'Image {i}: start',flush=True)
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
                image=im.convert('RGB')
            result={}
            if reader is not None:
                ocr_start=time.monotonic()
                try:
                    lines=read_ocr(path,reader)
                    from .adaptive_identity import identify_adaptive
                    ocr_elapsed=time.monotonic()-ocr_start
                    result=identify_adaptive(lines,lambda: visual(image))
                    result['ocr_lines']=lines
                except Exception as exc:
                    result['ocr_error']=str(exc)
                result['ocr_seconds']=ocr_elapsed if 'ocr_lines' in result else time.monotonic()-ocr_start
                if 'ocr_error' in result:
                    raise RuntimeError(result['ocr_error'])
            else:
                result=visual(image)
        except Exception as exc:
            result={'status':'FAILED','error':str(exc)}
        results.append(dict(index=i,elapsed_seconds=time.monotonic()-start,**result))
        print(f'Image {i}: {result.get("status")} elapsed={time.monotonic()-start:.1f}s',flush=True)
        output.write_text(json.dumps({'human_validation':'PENDING','results':results},ensure_ascii=False,indent=2),encoding='utf-8')
    if any(x['status']=='FAILED' or not x.get('fields') or (a.ocr and (not x.get('ocr_lines') or 'fusion' not in x)) for x in results):
        raise SystemExit('IDENTITY_GATE_FAILED')
if __name__=='__main__': main()
