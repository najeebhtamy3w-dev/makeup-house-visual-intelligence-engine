"""Synthetic smoke fixtures, not real-world accuracy benchmarks."""
import argparse
import json
from PIL import Image, ImageDraw, ImageFont
from .vision_models import OCRReader, VisualEncoder
from .classification import Classifier

def fixture():
    im=Image.new('RGB',(1000,500),'white')
    draw=ImageDraw.Draw(im)
    font=ImageFont.truetype('DejaVuSans.ttf',64)
    draw.text((70,70),'VITAMIN C SERUM',font=font,fill='black')
    draw.text((70,180),'100 ml',font=font,fill='black')
    return im

def main():
    p=argparse.ArgumentParser()
    p.add_argument('model',choices=['ocr','clip'])
    p.add_argument('--weights')
    args=p.parse_args()
    im=fixture()
    if args.model=='ocr':
        from paddleocr import PaddleOCR
        reader=OCRReader(PaddleOCR(lang='en',use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False))
        rows=reader.read(im)
        text=' '.join(x['text'] for x in rows).upper()
        passed='VITAMIN' in text and '100' in text
        report=dict(model='ocr',fixture='synthetic',passed=passed,rows=rows)
    else:
        encoder=VisualEncoder(args.weights)
        same=encoder.similarity(im,im)
        other=encoder.similarity(im,Image.new('RGB',im.size,'blue'))
        result=Classifier(encoder).classify(im)
        passed=0.99<=same<=1.001 and same>other and len(result['cosine_scores'])==7
        report=dict(model='clip',fixture='synthetic',passed=passed,self_similarity=same,other_similarity=other,classification=result)
    print(json.dumps(report,indent=2))
    if not passed:
        raise SystemExit(1)

if __name__=='__main__':
    main()
