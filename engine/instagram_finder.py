"""Instagram-only public indexed post discovery. No authentication bypass."""
from urllib.parse import urlsplit
from pathlib import Path
from .integration_core import discover
from .priority_discovery import instagram_post
from .candidate_quality import distance

HOSTS=("instagram.com","cdninstagram.com","fbcdn.net")

def find(query,search,output,target=20):
    if not isinstance(query,str) or not query.strip() or len(query)>215 or not 1<=target<=50:
        raise ValueError("INVALID_INPUT")
    hits=[h for h in search(query+" site:instagram.com") if instagram_post(h)]
    result=discover(query,lambda _:hits,HOSTS,Path(output),max_pages=10,max_images=50)
    selected=[]; rejected=[]
    for row in result["candidates"]:
        path=urlsplit(row["url"]).path.lower()
        if not instagram_post({"url":row["source"]}) or any(x in path for x in ("logo","favicon","sprite","profile_pic")) or min(row["width"],row["height"])<600:
            rejected.append(row["sha256"]); continue
        if any(distance(row["quality"]["dhash"],x["quality"]["dhash"])<=4 for x in selected):
            rejected.append(row["sha256"]); continue
        selected.append({**row,"discovery_stage":"instagram","identity_verified":False,"publication_allowed":False})
    selected.sort(key=lambda x:-min(x["width"],x["height"]))
    return {"query":query,"status":"REVIEW_REQUIRED" if selected else "NO_CANDIDATES","candidates":selected[:target],"filtered_hits":len(hits),"rejected":rejected,"errors":result["errors"],"diagnostics":getattr(search,"last_diagnostics",{}),"publication_allowed":False}
