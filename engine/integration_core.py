"""Bounded discovery pipeline for a trusted backend; never grants publication rights."""
from pathlib import Path
from .deep_extraction import extract
from .safe_download import Downloader, inspect_image
from .candidate_quality import assess, distance
from .image_selection import rank_candidates
from .catalog_evidence import extract_catalog
from .sku_evidence import compare

def discover(query, search, allowed_hosts, output, max_pages=5, max_images=20, downloader=None, visual_evaluator=None, purpose='catalog', expected_fields=None):
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
            html=raw.decode('utf-8','replace')
            candidates=extract(final,html,limit=20)
            catalog=extract_catalog(final,html) if expected_fields else []
            comparisons=[compare(expected_fields,x['fields']) for x in catalog]
            # Page-level evidence cannot establish the identity of every image.
            page_conflict=bool(comparisons) and all(x['status']=='CONFLICT' for x in comparisons)
        except Exception as exc:
            errors.append({'source':page,'error':type(exc).__name__,'detail':str(exc)[:240]})
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
                rows.append({**info,'url':url,'source':final,'file':path.name,'quality':quality,'page_sku_evidence':comparisons,'page_sku_conflict':page_conflict,'possible_duplicate_of':near,'identity_verified':False,'publication_allowed':False})
            except Exception as exc:
                errors.append({'source':candidate['url'],'error':type(exc).__name__,'detail':str(exc)[:240]})
        if attempts>=max_images: break
    if visual_evaluator is not None:
        for row in rows:
            try:
                row['visual_evidence']=visual_evaluator(output/row['file'],query)
            except Exception as exc:
                errors.append({'source':row['url'],'error':type(exc).__name__,'detail':str(exc)[:240],'stage':'VISUAL_EVALUATION'})
    for row in rows:
        if row['page_sku_conflict']:
            row.setdefault('visual_evidence',{})['identity_status']='CONFLICT'
    rows=rank_candidates(rows,purpose)
    return {'schema_version':'1.0','status':'REVIEW_REQUIRED' if rows else 'NO_CANDIDATES','query':query,'candidates':rows,'errors':errors,'attempts':attempts,'publication_allowed':False}
