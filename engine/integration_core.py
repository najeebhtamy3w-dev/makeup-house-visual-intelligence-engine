"""Bounded discovery pipeline for a trusted backend; never grants publication rights."""
from pathlib import Path
from .deep_extraction import extract
from .safe_download import Downloader, inspect_image
from .candidate_quality import assess, distance
from .image_selection import rank_candidates

def discover(query, search, allowed_hosts, output, max_pages=5, max_images=20, downloader=None, visual_evaluator=None, purpose='catalog'):
    if not isinstance(query,str) or not query.strip() or len(query)>240:
        raise ValueError('INVALID_QUERY')
    if not 1<=max_pages<=10 or not 1<=max_images<=50:
        raise ValueError('INVALID_LIMIT')
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    dl=downloader or Downloader(allowed_hosts)
    rows=[]; errors=[]; seen=set(); attempts=0
    for hit in list(search(query))[:max_pages]:
        page=hit['url']
        try:
            raw,_,final=dl.fetch(page,2000000,'text/html')
            candidates=extract(final,raw.decode('utf-8','replace'),limit=20)
        except Exception as exc:
            errors.append({'source':page,'error':type(exc).__name__})
            continue
        for candidate in candidates:
            if attempts>=max_images: break
            attempts+=1
            try:
                data,mime,url=dl.fetch(candidate['url'],10000000,'image/')
                info=inspect_image(data,mime)
                digest=info['sha256']
                if digest in seen: continue
                seen.add(digest)
                path=output/(digest+'.bin')
                path.write_bytes(data)
                quality=assess(path)
                near=next((r['sha256'] for r in rows if distance(r['quality']['dhash'],quality['dhash'])<=4),None)
                rows.append({**info,'url':url,'source':final,'file':path.name,'quality':quality,'possible_duplicate_of':near,'identity_verified':False,'publication_allowed':False})
            except Exception as exc:
                errors.append({'source':candidate['url'],'error':type(exc).__name__})
        if attempts>=max_images: break
    if visual_evaluator is not None:
        for row in rows:
            try:
                row['visual_evidence']=visual_evaluator(output/row['file'],query)
            except Exception as exc:
                errors.append({'source':row['url'],'error':type(exc).__name__,'stage':'VISUAL_EVALUATION'})
    rows=rank_candidates(rows,purpose)
    return {'schema_version':'1.0','status':'REVIEW_REQUIRED' if rows else 'NO_CANDIDATES','query':query,'candidates':rows,'errors':errors,'attempts':attempts,'publication_allowed':False}
