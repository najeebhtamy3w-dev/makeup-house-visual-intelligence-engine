import argparse
import json
import resource
import time
from PIL import Image, ImageDraw, ImageFont
from .multimodal import QwenIdentity

def main():
    p=argparse.ArgumentParser()
    p.add_argument('model_dir')
    args=p.parse_args()
    start=time.monotonic()
    model=QwenIdentity(args.model_dir)
    load=time.monotonic()-start
    im=Image.new('RGB',(640,640),'white')
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((100,50,540,590),radius=30,fill='#dce8ec',outline='black',width=3)
    font=ImageFont.truetype('DejaVuSans.ttf',42)
    for y,line in [(150,'TESTBRAND'),(240,'VITAMIN C'),(300,'SERUM'),(420,'100 ml')]:
        d.text((320,y),line,font=font,fill='black',anchor='mm')
    start=time.monotonic()
    result=model.identify(im)
    elapsed=time.monotonic()-start
    fields=result['fields']
    passed='testbrand' in fields.get('brand','').lower().replace(' ','') and 'serum' in fields.get('name','').lower() and '100' in fields.get('size','')
    print(json.dumps(dict(fixture='synthetic',passed=passed,load_seconds=load,inference_seconds=elapsed,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,result=result),indent=2))
    if not passed:
        raise SystemExit(1)

if __name__=='__main__':
    main()
