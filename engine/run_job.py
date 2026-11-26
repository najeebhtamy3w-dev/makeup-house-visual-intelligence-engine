import argparse
import json
import os
from pathlib import Path
from PIL import Image
from .pipeline import run_product
from .safe_download import Downloader
from .vision_models import BarcodeReader, OCRReader, VisualEncoder
from .classification import Classifier
from .multimodal import QwenIdentity

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--name',default='')
    p.add_argument('--image',required=True)
    p.add_argument('--host',action='append',required=True)
    p.add_argument('--seed',action='append',default=[])
    p.add_argument('--output',required=True)
    p.add_argument('--qwen-dir')
    p.add_argument('--clip-weights')
    p.add_argument('--ocr',action='store_true')
    p.add_argument('--barcode',action='store_true')
    args=p.parse_args()
    identity=QwenIdentity(args.qwen_dir) if args.qwen_dir else None
    encoder=VisualEncoder(args.clip_weights) if args.clip_weights else None
    ocr=None
    if args.ocr:
        from paddleocr import PaddleOCR
        ocr=OCRReader(PaddleOCR(lang='en',use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False))
    output=Path(args.output)
    with Image.open(args.image) as im:
        if im.width*im.height>25000000:
            raise ValueError('REFERENCE_PIXEL_LIMIT')
        report=run_product(args.name,im.convert('RGB'),{},Downloader(args.host),endpoint=os.environ.get('SEARXNG_ENDPOINT'),seeds=args.seed,barcode=BarcodeReader() if args.barcode else None,ocr=ocr,encoder=encoder,classifier=Classifier(encoder) if encoder else None,output_dir=output,identity_model=identity)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(report['status'])

if __name__=='__main__':
    main()
