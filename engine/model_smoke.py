import argparse
import json
from PIL import Image
from .vision_models import BarcodeReader, OCRReader, VisualEncoder

def run(args):
    import zxingcpp
    barcode = zxingcpp.create_barcode('4006381333931', zxingcpp.BarcodeFormat.EAN13)
    image = Image.fromarray(zxingcpp.write_barcode_to_image(barcode, scale=4))
    rows = BarcodeReader().read(image)
    assert any(x['text']=='4006381333931' and x['valid_gtin'] for x in rows), rows
    report={'barcode':'PASS','ocr':'NOT_CONFIGURED','clip':'NOT_CONFIGURED'}
    if args.ocr_image:
        from paddleocr import PaddleOCR
        reader=OCRReader(PaddleOCR(lang='en',use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False))
        with Image.open(args.ocr_image) as im:
            rows=reader.read(im)
        assert rows, 'OCR returned no text'
        report['ocr']={'status':'INFERENCE_EXECUTED','rows':rows}
    if args.clip_weights:
        encoder=VisualEncoder(args.clip_weights)
        score=encoder.similarity(image,image)
        assert 0.99 <= score <= 1.001, score
        report['clip']={'status':'INFERENCE_EXECUTED','self_similarity':score}
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--ocr-image')
    p.add_argument('--clip-weights')
    run(p.parse_args())
