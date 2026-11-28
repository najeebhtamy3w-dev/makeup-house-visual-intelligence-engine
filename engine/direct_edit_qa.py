"""Independent evidence for direct-edit human review, never automatic SKU approval."""
import math
import re
import unicodedata
from decimal import Decimal
from pathlib import Path
from PIL import Image


def _json_evidence(value):
    """An invalid numeric model result must not leak NaN/Infinity into JSON."""
    if isinstance(value,float) and not math.isfinite(value):
        return None
    if isinstance(value,dict):
        return {key:_json_evidence(item) for key,item in value.items()}
    if isinstance(value,(tuple,list)):
        return [_json_evidence(item) for item in value]
    return value


def _text(lines):
    return ' '.join(str(row.get('text','')) for row in lines
                    if isinstance(row.get('score'),(int,float))
                    and not isinstance(row.get('score'),bool)
                    and math.isfinite(row['score']) and .8<=row['score']<=1)


def _quantities(text):
    text=unicodedata.normalize('NFKC',text).casefold().replace('٫','.').replace('٪','%')
    text=''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)
    units={'ml':('ml',1),'مل':('ml',1),'ملل':('ml',1),
           'l':('ml',1000),'لتر':('ml',1000),
           'g':('g',1),'جم':('g',1),'غ':('g',1),'غرام':('g',1),
           'kg':('g',1000),'كجم':('g',1000),'كغ':('g',1000),
           'oz':('oz',1),'fl oz':('fl_oz',1),'%':('%',1)}
    alternatives='|'.join(re.escape(unit) for unit in sorted(units,key=len,reverse=True))
    pattern=r'(?<![\w.])([0-9]+(?:[.,][0-9]+)?)\s*('+alternatives+r')(?!\w)'
    result=set()
    for match in re.finditer(pattern,text):
        unit,multiplier=units[match[2]]
        # Preserve decimal quantity exactly; no approximate brand/number correction.
        number=match[1]
        if re.fullmatch(r'[1-9][0-9]{0,2},[0-9]{3}',number):
            # A comma may mean a decimal or a thousands separator. Keep it
            # unresolved rather than falsely equating 1,000 ml with 1 ml.
            result.add(('AMBIGUOUS:'+number,unit))
        else:
            value=Decimal(number.replace(',','.'))*multiplier
            result.add((format(value.normalize(),'f'),unit))
    return result


def _quantity_rows(values):
    return [{'value':value,'unit':unit} for value,unit in sorted(values)]


def assess_edit(source,output,evaluator=None,ocr=None):
    result={'status':'REVIEW_REQUIRED','identity_verified':False,'publication_allowed':False,'warnings':[],
            'visual_evidence_status':'UNAVAILABLE','ocr_evidence_status':'UNAVAILABLE'}
    with Image.open(output) as im:
        if im.width*im.height>25000000: raise ValueError('PIXEL_LIMIT')
        result['dimensions']=list(im.size)
        im.verify()
    if evaluator is not None:
        try:
            visual=evaluator.for_reference(source)(output,'cosmetic product photograph')
            result['visual']=_json_evidence(visual)
            similarity=visual.get('similarity_cosine') if isinstance(visual,dict) else None
            if (isinstance(similarity,bool) or not isinstance(similarity,(int,float))
                    or not math.isfinite(similarity) or not -1<=similarity<=1):
                result['visual_evidence_status']='INVALID'
                result['warnings'].append('VISUAL_SIMILARITY_INVALID')
            else:
                result['visual_evidence_status']='MODEL_HYPOTHESIS'
                if similarity<.85:
                    result['warnings'].append('LOW_VISUAL_SIMILARITY')
        except Exception as exc:
            result['visual_evidence_status']='FAILED'
            result['warnings'].append('VISUAL_QA_FAILED:'+type(exc).__name__)
    else: result['warnings'].append('VISUAL_QA_UNAVAILABLE')
    if ocr is not None:
        try:
            from .identity_fusion import read_ocr
            before_text=_text(read_ocr(Path(source),ocr))
            after_text=_text(read_ocr(Path(output),ocr))
            before=set(re.findall(r'\w+',before_text.casefold()))
            after=set(re.findall(r'\w+',after_text.casefold()))
            result['ocr_evidence_status']='OCR_HYPOTHESIS' if before else 'SOURCE_UNCERTAIN'
            result['ocr_missing_tokens']=sorted(before-after)
            if not before: result['warnings'].append('SOURCE_TEXT_UNCERTAIN')
            elif before-after: result['warnings'].append('PRODUCT_TEXT_MAY_HAVE_CHANGED')
            before_numbers,after_numbers=_quantities(before_text),_quantities(after_text)
            if any(value.startswith('AMBIGUOUS:') for value,unit in before_numbers|after_numbers):
                result['warnings'].append('AMBIGUOUS_NUMERIC_FORMAT_REQUIRES_REVIEW')
            result['ocr_source_quantities']=_quantity_rows(before_numbers)
            result['ocr_edited_quantities']=_quantity_rows(after_numbers)
            result['ocr_missing_quantities']=_quantity_rows(before_numbers-after_numbers)
            result['ocr_added_quantities']=_quantity_rows(after_numbers-before_numbers)
            if before_numbers-after_numbers:
                result['warnings'].append('PRODUCT_NUMERIC_TEXT_MAY_HAVE_CHANGED')
            if after_numbers-before_numbers:
                result['warnings'].append('ADDED_NUMERIC_TEXT_REQUIRES_REVIEW')
        except Exception as exc:
            result['ocr_evidence_status']='FAILED'
            result['warnings'].append('OCR_QA_FAILED:'+type(exc).__name__)
    else: result['warnings'].append('OCR_QA_UNAVAILABLE')
    return result
