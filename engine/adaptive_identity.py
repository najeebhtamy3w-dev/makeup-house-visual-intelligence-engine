"""Execute OCR-first routing without treating search hits as verified identity."""
from .identity_fusion import route, strong_lines, fuse
from .sku_evidence import compare
from .catalog_evidence import collect_catalog
import time
from .fast_identity import fast_candidate

def identify_adaptive(lines, visual, search=None, structured_evidence=None, catalog_downloader=None):
    decision=route(lines)
    query=' '.join(strong_lines(lines))[:240]
    hits=[]
    search_start=time.monotonic()
    error=None
    if decision['route']=='EXTERNAL_SEARCH_FIRST' and search is not None:
        try:
            hits=list(search(query))[:10]
        except Exception as exc:
            error=type(exc).__name__
    search_seconds=time.monotonic()-search_start
    catalog=collect_catalog(hits,catalog_downloader) if catalog_downloader is not None else {'evidence':[],'errors':[]}
    evidence=(list(structured_evidence or [])+catalog['evidence'])[:20]
    candidate=fast_candidate(lines,evidence)
    start=time.monotonic()
    result=visual() if candidate is None else {'fields':candidate,'status':'OCR_CATALOG_HYPOTHESIS'}
    result['visual_seconds']=time.monotonic()-start
    result['fusion']=fuse(result.get('fields',{}),lines)
    result['adaptive']={'decision':decision['route'],'query':query,'search_attempted':decision['route']=='EXTERNAL_SEARCH_FIRST' and search is not None,'search_hits':hits,'search_seconds':search_seconds,'search_error':error,'visual_executed':candidate is None,'verified':False}
    if candidate is not None:
        for field in result['fusion']['fields'].values(): field['source']='OCR_CATALOG'
    result['catalog_evidence']=catalog
    comparisons=[]
    for item in evidence:
        comparisons.append({'source':item['source'],'comparison':compare(result.get('fields',{}),item['fields'])})
    result['sku_evidence']=comparisons
    result['identity_verified']=False
    return result
