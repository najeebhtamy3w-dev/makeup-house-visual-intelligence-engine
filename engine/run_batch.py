import argparse,json,os
from pathlib import Path
from PIL import Image
from .batch import Batch
from .pipeline import run_product
from .safe_download import Downloader
from .vision_models import BarcodeReader,OCRReader,VisualEncoder
from .classification import Classifier
from .multimodal import QwenIdentity
from .aesthetic import AestheticPredictor
from .background import BackgroundRemover
from .studio_job import prepare

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--queue',required=True)
    p.add_argument('--manifest')
    p.add_argument('--host',action='append',required=True)
    p.add_argument('--clip-weights')
    p.add_argument('--qwen-dir')
    p.add_argument('--ocr',action='store_true')
    p.add_argument('--barcode',action='store_true')
    p.add_argument('--aesthetic-clip')
    p.add_argument('--aesthetic-head')
    p.add_argument('--aesthetic-sha256')
    p.add_argument('--studio',action='store_true')
    p.add_argument('--remove-background',action='store_true')
    p.add_argument('--limit',type=int,default=100)
    a=p.parse_args()
    options=(a.aesthetic_clip,a.aesthetic_head,a.aesthetic_sha256)
    if any(options) and not all(options): p.error('All aesthetic options required')
    if a.remove_background and not a.studio: p.error('Background removal requires studio')
    queue=Batch(a.queue)
    try:
        if a.manifest:
            path=Path(a.manifest).resolve()
            rows=json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(rows,list) or len(rows)>10000: raise ValueError('INVALID_MANIFEST')
            for row in rows:
                image=(path.parent/row['image']).resolve()
                if not image.is_relative_to(path.parent): raise ValueError('INVALID_IMAGE_PATH')
                queue.add(row.get('name',''),image,row.get('fields'),row.get('seeds',[]))
        encoder=VisualEncoder(a.clip_weights) if a.clip_weights else None
        classifier=Classifier(encoder) if encoder else None
        identity=QwenIdentity(a.qwen_dir) if a.qwen_dir else None
        barcode=BarcodeReader() if a.barcode else None
        ocr=None
        if a.ocr:
            from paddleocr import PaddleOCR
            ocr=OCRReader(PaddleOCR(lang='en',use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False))
        aesthetic=AestheticPredictor(VisualEncoder(options[0],'ViT-L-14'),options[1],options[2]) if all(options) else None
        remover=BackgroundRemover() if a.remove_background else None
        client=Downloader(a.host)
        def process(payload,folder):
            with Image.open(folder/'reference.bin') as im:
                if im.width*im.height>25000000: raise ValueError('REFERENCE_PIXEL_LIMIT')
                report=run_product(payload['name'],im.convert('RGB'),payload['fields'],client,endpoint=os.environ.get('SEARXNG_ENDPOINT'),seeds=payload['seeds'],barcode=barcode,ocr=ocr,encoder=encoder,classifier=classifier,identity_model=identity,aesthetic=aesthetic,output_dir=folder)
            if a.studio:
                report['studio']=prepare(report,folder,remover)
            return report
        print(json.dumps(queue.run(process,limit=a.limit)))
    finally:
        queue.close()

if __name__=='__main__': main()
