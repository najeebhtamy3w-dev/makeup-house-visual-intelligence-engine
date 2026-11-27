"""Evidence for human review, not automatic SKU approval."""
from pathlib import Path
from PIL import Image

def assess_edit(source,output,evaluator=None,ocr=None):
    result={'status':'REVIEW_REQUIRED','identity_verified':False,'publication_allowed':False,'warnings':[]}
    with Image.open(output) as im:
        if im.width*im.height>25000000: raise ValueError('PIXEL_LIMIT')
        result['dimensions']=list(im.size)
        im.verify()
    if evaluator is not None:
        try:
            result['visual']=evaluator.for_reference(source)(output,'cosmetic product photograph')
            if (result['visual'].get('similarity_cosine') or 0)<.85:
                result['warnings'].append('LOW_VISUAL_SIMILARITY')
        except Exception as exc:
            result['warnings'].append('VISUAL_QA_FAILED:'+type(exc).__name__)
    else: result['warnings'].append('VISUAL_QA_UNAVAILABLE')
    if ocr is not None:
        try:
            from .identity_fusion import read_ocr
            import re
            def tokens(path):
                lines=read_ocr(Path(path),ocr)
                return set(re.findall(r'\w+',' '.join(str(x.get('text','')) for x in lines if x.get('score',0)>=.8).casefold()))
            before,after=tokens(source),tokens(output)
            result['ocr_missing_tokens']=sorted(before-after)
            if not before: result['warnings'].append('SOURCE_TEXT_UNCERTAIN')
            elif before-after: result['warnings'].append('PRODUCT_TEXT_MAY_HAVE_CHANGED')
        except Exception as exc:
            result['warnings'].append('OCR_QA_FAILED:'+type(exc).__name__)
    else: result['warnings'].append('OCR_QA_UNAVAILABLE')
    return result
