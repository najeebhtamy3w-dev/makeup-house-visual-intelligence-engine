"""Live acceptance; requires operator-configured SearXNG and source allowlist."""
import argparse
import json
import time
from pathlib import Path
from .integration_core import discover
from .search_discovery import SearxDiscovery

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--endpoint',required=True)
    p.add_argument('--host',action='append',required=True)
    p.add_argument('--output',default='results-integration')
    a=p.parse_args()
    root=Path(a.output)
    root.mkdir(parents=True,exist_ok=True)
    search=SearxDiscovery(a.endpoint)
    queries=['CeraVe Hydrating Facial Cleanser site:cerave.com','Pura Dor Vitamin C Serum site:purador.com','Maybelline Sky High Mascara site:maybelline.com']
    reports=[]
    for i,q in enumerate(queries):
        start=time.monotonic()
        try:
            result=discover(q,search,a.host,root/str(i),max_pages=3,max_images=10)
        except Exception as exc:
            result={'query':q,'status':'FAILED','error':type(exc).__name__,'candidates':[]}
        result['elapsed_seconds']=time.monotonic()-start
        reports.append(result)
        (root/'report.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
        print(json.dumps({'query':q,'status':result['status'],'count':len(result['candidates'])}),flush=True)
    (root/'report.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
    if not all(r['candidates'] and not r.get('publication_allowed',False) for r in reports):
        raise SystemExit('LIVE_DISCOVERY_GATE_FAILED')

if __name__=='__main__':
    main()
