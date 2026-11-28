"""Prepare review-only derivatives from ranked local candidates."""
import hashlib
from pathlib import Path
from .studio import render
from .background import preview

def prepare(report, directory, remover=None, limit=3):
    root=Path(directory).resolve()
    if not 1<=limit<=10:
        raise ValueError('INVALID_STUDIO_LIMIT')
    target=root/'studio'
    target.mkdir(exist_ok=True)
    results=[]
    for row in report.get('ranked_candidates',[])[:limit]:
        try:
            path=(root/row['file']).resolve()
            if path.parent!=root or path.stat().st_size>10000000:
                raise ValueError('INVALID_SOURCE_FILE')
            data=path.read_bytes()
            digest=hashlib.sha256(data).hexdigest()
            if digest!=row['sha256']:
                raise ValueError('SOURCE_HASH_MISMATCH')
            source=row['url']
            for label,size,bg in [('store',(1080,1080),'#ffffff'),('story',(1080,1920),'#f4e5eb')]:
                out,meta=preview(data,source,remover,size=size,background=bg) if remover is not None else render(data,source,size=size,background=bg)
                filename=digest+'-'+label+'.png'
                (target/filename).write_bytes(out)
                results.append(dict(meta,file='studio/'+filename,preset=label))
        except Exception as exc:
            results.append(dict(source_sha256=row.get('sha256'),status='STUDIO_FAILED',error=str(exc),commercial_approved=False))
    return results
