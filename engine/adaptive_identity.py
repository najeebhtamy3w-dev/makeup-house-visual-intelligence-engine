"""Execute OCR-first routing without treating search hits as verified identity."""
from .identity_fusion import route, strong_lines, fuse
from .sku_evidence import compare
from .catalog_evidence import collect_catalog
import time

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
    # Search discovery is not verification; only explicit corroboration can skip visual inference.
    start=time.monotonic()
    result=visual()
    result['visual_seconds']=time.monotonic()-start
    result['fusion']=fuse(result.get('fields',{}),lines)
    result['adaptive']={'decision':decision['route'],'query':query,'search_attempted':decision['route']=='EXTERNAL_SEARCH_FIRST' and search is not None,'search_hits':hits,'search_seconds':search_seconds,'search_error':error,'visual_executed':True,'verified':False}
    catalog=collect_catalog(hits,catalog_downloader) if catalog_downloader is not None else {'evidence':[],'errors':[]}
    result['catalog_evidence']=catalog
    comparisons=[]
    for item in (list(structured_evidence or [])+catalog['evidence'])[:20]:
        comparisons.append({'source':item['source'],'comparison':compare(result.get('fields',{}),item['fields'])})
    result['sku_evidence']=comparisons
    result['identity_verified']=False
    return result
