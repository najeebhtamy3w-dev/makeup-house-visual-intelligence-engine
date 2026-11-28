import io,json,time
from pathlib import Path
from PIL import Image,ImageDraw
from .background import BackgroundRemover,preview

def main():
    root=Path('background-results')
    root.mkdir(exist_ok=True)
    start=time.monotonic()
    model=BackgroundRemover()
    load=time.monotonic()-start
    im=Image.new('RGB',(512,512),'#d9dce3')
    truth=Image.new('L',im.size)
    for target,fill in [(im,'#63383d'),(truth,255)]:
        d=ImageDraw.Draw(target)
        d.rounded_rectangle((170,130,342,440),radius=22,fill=fill)
        d.rectangle((205,65,307,140),fill=fill)
    ImageDraw.Draw(im).text((215,250),'SERUM',fill='white')
    im.save(root/'input.png')
    start=time.monotonic()
    mask=model.mask(im)
    elapsed=time.monotonic()-start
    mask.save(root/'mask.png')
    pairs=list(zip(mask.getdata(),truth.getdata()))
    union=sum(a>=128 or b>=128 for a,b in pairs)
    iou=sum(a>=128 and b>=128 for a,b in pairs)/union
    class Cached:
        def mask(self,image): return mask
    out,meta=preview((root/'input.png').read_bytes(),'synthetic fixture',Cached())
    (root/'preview.png').write_bytes(out)
    report=dict(load_seconds=load,inference_seconds=elapsed,iou=iou,fixture='synthetic opaque bottle',metadata=meta)
    (root/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
    if iou<.65: raise SystemExit('SEGMENTATION_GATE_FAILED')
if __name__=='__main__': main()
