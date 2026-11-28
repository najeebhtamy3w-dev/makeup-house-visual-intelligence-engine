"""Deterministic end-to-end acceptance; not a live commercial benchmark."""
import io,json,time
from pathlib import Path
from PIL import Image,ImageDraw
from .batch import Batch
from .pipeline import run_product
from .studio_job import prepare

class FixtureClient:
    allowed_hosts=['example.org']
    def __init__(self,data): self.data=data
    def fetch(self,url,limit,mime):
        if mime=='text/html':
            return b'<html><img src="https://example.org/product.png" width="800"></html>','text/html',url
        return self.data,'image/png',url

def run(root,count):
    root=Path(root)
    root.mkdir(parents=True,exist_ok=True)
    q=Batch(root/'queue')
    start=time.monotonic()
    try:
        for i in range(count):
            im=Image.new('RGB',(800,800),'white')
            d=ImageDraw.Draw(im)
            d.rectangle((250,150,550,700),fill=(70+i%150,50,90))
            d.text((300,400),f'FIXTURE {i}',fill='white')
            p=root/f'input-{i}.png'
            im.save(p)
            q.add(f'Fixture {i}',p,seeds=['https://example.org/page'])
        def process(payload,folder):
            data=(folder/'reference.bin').read_bytes()
            with Image.open(io.BytesIO(data)) as im:
                report=run_product(payload['name'],im.convert('RGB'),{},FixtureClient(data),seeds=payload['seeds'],output_dir=folder)
            report['studio']=prepare(report,folder)
            if not report['ranked_candidates'] or len(report['studio'])!=2 or any(x.get('commercial_approved') or x.get('status')=='STUDIO_FAILED' for x in report['studio']):
                raise ValueError('FIXTURE_ACCEPTANCE_FAILED')
            return report
        q.run(process,limit=max(1,count//2))
        q.close()
        q=Batch(root/'queue')
        summary=q.run(process,limit=count)
        report=dict(fixture_type='synthetic',network=False,real_models=False,count=count,states=summary,elapsed_seconds=time.monotonic()-start,passed=summary=={'REVIEW_REQUIRED':count})
        (root/'acceptance.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report))
        if not report['passed']: raise SystemExit(1)
    finally:
        q.close()

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--count',type=int,choices=[3,10,30,100],default=10)
    p.add_argument('--output',default='batch-results')
    a=p.parse_args()
    run(a.output,a.count)
