"""Standalone image discovery; candidates require human identity and rights review."""
import argparse
import json
from pathlib import Path
from .integration_core import discover
from .priority_discovery import instagram_post
from .safe_download import Downloader
from .search_discovery import SearxDiscovery

def find(query, search, hosts, output, target=5):
    if not query.strip() or len(query)>215 or not 1<=target<=20:
        raise ValueError("INVALID_INPUT")
    output=Path(output)
    dl=Downloader(hosts)
    rows={}; stages=[]
    for stage in ("instagram","web"):
        try:
            hits=list(search(query+" site:instagram.com" if stage=="instagram" else query))
            hits=[h for h in hits if instagram_post(h)==(stage=="instagram")]
            result=discover(query,lambda _:hits,hosts,output,max_pages=10,max_images=40,downloader=dl)
            for row in result["candidates"]:
                if min(row["width"],row["height"])<600:
                    continue
                if row["sha256"] not in rows:
                    rows[row["sha256"]]={**row,"discovery_stage":stage,"identity_verified":False,"publication_allowed":False}
            stages.append({"stage":stage,"hits":len(hits),"errors":result["errors"],"diagnostics":getattr(search,"last_diagnostics",{})})
        except Exception as exc:
            stages.append({"stage":stage,"error":type(exc).__name__,"detail":str(exc)[:240]})
        # Without identity models, always offer web alternatives for human review.
    from .candidate_quality import distance
    selected=[]
    for row in sorted(rows.values(),key=lambda x:(x["discovery_stage"]!="instagram",-min(x["width"],x["height"]))):
        if any(distance(row["quality"]["dhash"],x["quality"]["dhash"])<=4 for x in selected):
            continue
        selected.append(row)
    return {"query":query,"status":"REVIEW_REQUIRED" if selected else "NO_CANDIDATES","stages":stages,"candidates":selected[:target],"publication_allowed":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--endpoint",required=True)
    p.add_argument("--host",action="append",required=True)
    p.add_argument("--query",action="append",required=True)
    p.add_argument("--output",default="finder-results")
    p.add_argument("--target",type=int,default=5)
    a=p.parse_args()
    if len(a.query)>100: p.error("maximum 100 products")
    root=Path(a.output); root.mkdir(parents=True,exist_ok=True)
    search=SearxDiscovery(a.endpoint)
    results=[]
    for i,q in enumerate(a.query):
        results.append(find(q,search,a.host,root/str(i),a.target))
        (root/"report.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
    if not all(x["candidates"] for x in results): raise SystemExit(1)

if __name__=="__main__": main()
