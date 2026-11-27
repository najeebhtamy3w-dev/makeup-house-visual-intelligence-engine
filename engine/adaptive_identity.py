"""Execute OCR-first routing without treating search hits as verified identity."""
from .identity_fusion import route, strong_lines, fuse
import time

def identify_adaptive(lines, visual, search=None):
    decision=route(lines)
    query=' '.join(strong_lines(lines))[:240]
    hits=[]
    error=None
    if decision['route']=='EXTERNAL_SEARCH_FIRST' and search is not None:
        try:
            hits=list(search(query))[:10]
        except Exception as exc:
            error=type(exc).__name__
    # Search discovery is not verification; only explicit corroboration can skip visual inference.
    start=time.monotonic()
    result=visual()
    result['visual_seconds']=time.monotonic()-start
    result['fusion']=fuse(result.get('fields',{}),lines)
    result['adaptive']={'decision':decision['route'],'query':query,'search_attempted':decision['route']=='EXTERNAL_SEARCH_FIRST' and search is not None,'search_hits':hits,'search_error':error,'visual_executed':True,'verified':False}
    return result
