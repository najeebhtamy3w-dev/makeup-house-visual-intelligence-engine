import json
import os
from pathlib import Path
from .benchmark import PAGES
from .pipeline import run_product
from .safe_download import Downloader

NAMES={'cerave':'CeraVe Hydrating Cleanser','purador':"Pura D'or Vitamin C Serum",'maybelline':'Maybelline Sky High Mascara'}
def main():
    root=Path('results-v081')
    root.mkdir(exist_ok=True)
    client=Downloader(['instagram.com','cdninstagram.com','cerave.com','purador.com','maybelline.com','cdn.shopify.com'],timeout=8)
    reports={}
    for key,seeds in PAGES.items():
        try:
            report=run_product(NAMES[key],None,{},client,endpoint=os.environ.get('SEARXNG_ENDPOINT'),seeds=seeds,max_pages=4,max_images=12,output_dir=root/key)
            report['stored_review_candidates']=sum(x.get('status')=='NEEDS_MANUAL_REVIEW' and bool(x.get('file')) and (root/key/x['file']).is_file() for x in report['images'])
        except Exception as exc:
            report={'status':'FAILED','error':str(exc),'stored_review_candidates':0}
        reports[key]=report
        (root/'report.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
    if not all(x['stored_review_candidates']>0 for x in reports.values()):
        raise SystemExit('LIVE_DISCOVERY_GATE_FAILED')

if __name__=='__main__':
    main()
