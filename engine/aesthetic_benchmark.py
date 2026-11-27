import argparse, hashlib, json, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from .vision_models import VisualEncoder
from .aesthetic import AestheticPredictor
from .ranking import rank_candidates

def main():
    p=argparse.ArgumentParser()
    p.add_argument('clip')
    p.add_argument('head')
    p.add_argument('sha256')
    a=p.parse_args()
    start=time.monotonic()
    model=AestheticPredictor(VisualEncoder(a.clip,'ViT-L-14'),a.head,a.sha256)
    load=time.monotonic()-start
    root=Path('aesthetic-results')
    root.mkdir(exist_ok=True)
    pairs=[]
    for index,color in enumerate(['#ecc9b8','#c4d8ce','#ddd0ea']):
        clean=Image.new('RGB',(640,640),color)
        d=ImageDraw.Draw(clean)
        d.ellipse((180,490,460,560),fill='#b5aaa5')
        d.rounded_rectangle((225,130,415,530),radius=25,fill='#fffefa',outline='#8c817c',width=3)
        d.rectangle((260,75,380,150),fill='#403936')
        d.text((275,300),'TEST SERUM',fill='black')
        degraded=ImageEnhance.Brightness(clean.filter(ImageFilter.GaussianBlur(12))).enhance(.25)
        rows=[]
        for label,im in [('clean',clean),('degraded',degraded)]:
            start=time.monotonic()
            result=model.evaluate(im)
            name=f'{index}-{label}.png'
            im.save(root/name)
            rows.append(dict(result=result,file=name,seconds=time.monotonic()-start))
        pairs.append(dict(images=rows,preferred=rows[0]['result']['raw_score']>rows[1]['result']['raw_score']))
    wins=sum(x['preferred'] for x in pairs)
    report=dict(load_seconds=load,head_sha256=a.sha256,encoder_sha256=hashlib.file_digest(open(a.clip,'rb'),'sha256').hexdigest(),pairs=pairs,wins=wins,fixture_type='synthetic',commercial_approved=False)
    (root/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if wins<2:
        raise SystemExit('AESTHETIC_PAIR_GATE_FAILED')

if __name__=='__main__':
    main()
