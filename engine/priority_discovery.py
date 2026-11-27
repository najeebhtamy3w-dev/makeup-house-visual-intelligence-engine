from urllib.parse import urlsplit
from .integration_core import discover

def instagram_post(hit):
    u=urlsplit(hit.get("url",""))
    return u.hostname in ("instagram.com","www.instagram.com") and u.path.startswith(("/p/","/reel/"))

def suitable_for_review(c):
    s=c.get("selection",{})
    v=c.get("visual_evidence",{})
    return (s.get("status")=="REVIEW_REQUIRED" and not c.get("page_sku_conflict")
        and not c.get("possible_duplicate_of") and min(c.get("width",0),c.get("height",0))>=600
        and s.get("components",{}).get("purpose_fit")==1.0
        and v.get("identity_status")=="CORROBORATED_REVIEW_REQUIRED"
        and (v.get("similarity_cosine") or 0)>=0.85)

def priority_discover(query,search,hosts,output,**kwargs):
    from pathlib import Path
    output=Path(output)
    stages=[]; candidates=[]
    for name in ("instagram","web"):
        try:
            q=query[:215]+" site:instagram.com" if name=="instagram" else query
            hits=list(search(q))
            hits=[h for h in hits if instagram_post(h)] if name=="instagram" else [h for h in hits if not instagram_post(h)]
            # Keep artifacts in the existing flat job directory for API retrieval.
            result=discover(query,lambda _:hits,hosts,output,**kwargs)
            stages.append({"stage":name,"status":result["status"],"errors":result["errors"],"count":len(result["candidates"])})
            candidates.extend(result["candidates"])
        except Exception as exc:
            stages.append({"stage":name,"status":"FAILED","error":type(exc).__name__})
        # Only stop on strong SKU evidence, never on raw search hits.
        if any(suitable_for_review(c) for c in candidates): break
    unique={c["sha256"]:c for c in reversed(candidates)}
    from .image_selection import rank_candidates
    rows=rank_candidates(list(unique.values()),kwargs.get("purpose","catalog"))
    return {"schema_version":"1.0","status":"REVIEW_REQUIRED" if rows else "NO_CANDIDATES","query":query,"candidates":rows,"stages":stages,"errors":[e for s in stages for e in s.get("errors",[])],"suitable_candidates":sum(suitable_for_review(c) for c in rows),"creative_fallback_suggested":not any(suitable_for_review(c) for c in rows),"creative_edit_available":True,"creative_fallback_requires_user_choice":True,"publication_allowed":False}
