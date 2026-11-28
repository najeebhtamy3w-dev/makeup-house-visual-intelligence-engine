import json,sys
from pathlib import Path
from PIL import Image
from .identity_fusion import read_ocr
from .candidate_ocr import assess_text

def main():
    from paddleocr import PaddleOCR
    root=Path(sys.argv[1])
    reports=json.loads((root/'report.json').read_text())
    reader=PaddleOCR(lang='en',use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False,device='cpu')
    evidence=[]
    for i,report in enumerate(reports):
        for row in report['candidates'][:5]:
            path=root/str(i)/row['file']
            # OCR backend needs a recognized image extension.
            temp=path.with_suffix('.ocr.png')
            with Image.open(path) as im: im.convert('RGB').save(temp)
            try:
                lines=read_ocr(temp,reader)
                evidence.append({'query':report['query'],'sha256':row['sha256'],'lines':lines})
            finally: temp.unlink(missing_ok=True)
            (root/'ocr-report.json').write_text(json.dumps(evidence,indent=2))
    if not evidence or not any(e['lines'] for e in evidence): raise SystemExit('OCR_EVIDENCE_MISSING')
if __name__=='__main__': main()
