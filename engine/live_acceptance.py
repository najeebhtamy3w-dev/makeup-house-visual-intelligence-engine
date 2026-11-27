"""Live acceptance using independently supplied product photos."""
import argparse,json,os,time
from pathlib import Path
from PIL import Image
from .pipeline import run_product
from .safe_download import Downloader
from .vision_models import BarcodeReader
from .studio_job import prepare

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--host',action='append',required=True)
    a=p.parse_args()
    manifest=Path(a.manifest).resolve()
    rows=json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(rows,list) or not 1<=len(rows)<=100:
        raise ValueError('INVALID_MANIFEST')
    root=Path(a.output)
    root.mkdir(parents=True,exist_ok=True)
    client=Downloader(a.host)
    barcode=BarcodeReader()
    reports=[]
    for i,row in enumerate(rows):
        start=time.monotonic()
        folder=root/str(i)
        folder.mkdir(exist_ok=True)
        try:
            path=(manifest.parent/row['image']).resolve()
            if not path.is_relative_to(manifest.parent): raise ValueError('INVALID_PATH')
            with Image.open(path) as im:
                if im.width*im.height>25000000: raise ValueError('PIXEL_LIMIT')
                report=run_product(row['name'],im.convert('RGB'),row.get('fields',{}),client,endpoint=os.environ.get('SEARXNG_ENDPOINT'),seeds=row.get('seeds',[]),barcode=barcode,output_dir=folder)
            report['studio']=prepare(report,folder)
            report['commercial_approved']=False
        except Exception as exc:
            report={'status':'FAILED','error':str(exc),'commercial_approved':False}
        report['elapsed_seconds']=time.monotonic()-start
        (folder/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
        reports.append({'index':i,'status':report['status'],'ranked':len(report.get('ranked_candidates',[])),'elapsed_seconds':report['elapsed_seconds']})
        (root/'summary.json').write_text(json.dumps({'mode':'live_barcode_only','human_sku_validation':'PENDING','products':reports},indent=2),encoding='utf-8')
    if any(x['status']!='REVIEW_REQUIRED' or not x['ranked'] for x in reports):
        raise SystemExit('LIVE_CANDIDATE_GATE_FAILED')
if __name__=='__main__': main()
