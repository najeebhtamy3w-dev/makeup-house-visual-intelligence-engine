"""Integrated review pipeline; network and inference adapters are injectable."""
import io
from pathlib import Path
from .multimodal import search_name
from PIL import Image
from .discovery import discover
from .deep_extraction import extract
from .safe_download import inspect_image, validate_url
from .visual_quality import signals, near_duplicate
from .sku_verification import verify

def run_product(name, reference, fields, client, endpoint=None, seeds=(), barcode=None, ocr=None, encoder=None, classifier=None, max_pages=8, max_images=40, output_dir=None, identity_model=None):
    hypothesis=None
    if identity_model is not None and reference is not None:
        try:
            hypothesis=identity_model.identify(reference)
            if not name.strip():
                name=search_name(hypothesis['fields'])
        except Exception as exc:
            hypothesis={'status':'MODEL_FAILED','error':str(exc)}
    if not name.strip() or not 1<=max_pages<=30 or not 1<=max_images<=200:
        raise ValueError('INVALID_JOB')
    report={'product':name,'discovery':[],'pages':[],'images':[],'commercial_approved':False}
    report['identity_hypothesis']=hypothesis
    destination=Path(output_dir) if output_dir is not None else None
    if destination is not None:
        destination.mkdir(parents=True,exist_ok=True)
    pages=list(dict.fromkeys(seeds))
    seen={}
    attempted=0
    visited=set()
    def process():
        nonlocal attempted
        for page in pages:
            if page in visited or len(visited)>=max_pages or attempted>=max_images:
                continue
            visited.add(page)
            try:
                raw,_,final=client.fetch(page,5000000,'text/html')
                rows=extract(final,raw.decode('utf-8','replace'),20)
                report['pages'].append({'url':page,'count':len(rows)})
                for row in rows:
                    if attempted>=max_images:
                        break
                    attempted+=1
                    try:
                        data,mime,url=client.fetch(row['url'],10000000,'image/')
                        row.update(inspect_image(data,mime),final_url=url)
                        digest=row['sha256']
                        if destination is not None:
                            suffix={'PNG':'.png','JPEG':'.jpg','WEBP':'.webp','GIF':'.gif'}.get(row['format'],'.bin')
                            filename=digest+suffix
                            (destination/filename).write_bytes(data)
                            row['file']=filename
                        if digest in seen:
                            row['status']='EXACT_DUPLICATE'
                        else:
                            with Image.open(io.BytesIO(data)) as im:
                                row.update(signals(im))
                                row['possible_duplicates']=[d for d,h in seen.items() if near_duplicate(h,row['dhash'])]
                                seen[digest]=row['dhash']
                                row['verification']=verify(reference,im,fields,{},barcode,ocr,encoder)
                                if classifier:
                                    row['classification']=classifier.classify(im)
                            row['status']='SKU_CONFLICT' if row['verification']['status']=='SKU_CONFLICT' else 'NEEDS_MANUAL_REVIEW'
                    except Exception as exc:
                        row.update(status='CANDIDATE_FAILED',error=str(exc))
                    report['images'].append(row)
            except Exception as exc:
                report['pages'].append({'url':page,'error':str(exc)})
    for query in (name,name+' product packaging',name+' official product photo'):
        if endpoint:
            for result in discover(query,endpoint,limit=12):
                report['discovery'].append(dict(query=query,**result))
                for hit in result['hits']:
                    try:
                        validate_url(hit['url'],client.allowed_hosts)
                    except ValueError:
                        continue
                    if hit['url'] not in pages:
                        pages.append(hit['url'])
        process()
        if not endpoint or len(visited)>=max_pages or attempted>=max_images or sum(x.get('status')=='NEEDS_MANUAL_REVIEW' for x in report['images'])>=5:
            break
    report['status']='REVIEW_REQUIRED' if any(x.get('status')=='NEEDS_MANUAL_REVIEW' for x in report['images']) else 'NO_REVIEW_CANDIDATES'
    return report
