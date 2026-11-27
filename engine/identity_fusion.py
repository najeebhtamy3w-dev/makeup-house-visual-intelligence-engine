import re
import unicodedata
import math
from difflib import SequenceMatcher

def normalize(value):
    return re.sub(r'[^\w]+', '', unicodedata.normalize('NFKC', str(value or '')).casefold())

def size_candidates(text):
    return sorted(set(re.findall(r'\b\d+(?:[.,]\d+)?\s*(?:m\s*[l1i]|k\s*g|g|oz)\b', unicodedata.normalize('NFKC',text).casefold())))

def canonical_size(text):
    from .sku_evidence import size
    normalized=re.sub(r'm[1i]$', 'ml', normalize(text))
    parsed=size(normalized)
    return format(parsed[0].normalize(),'f')+parsed[1] if parsed else normalized

def strong_lines(lines):
    result=[]
    for row in lines:
        if not isinstance(row,dict) or not isinstance(row.get('text'),str): continue
        try: score=float(row.get('score',0))
        except (ValueError,TypeError): continue
        if not isinstance(row.get('score'),bool) and math.isfinite(score) and .8<=score<=1:
            result.append(row['text'])
    return result

def route(lines):
    strong=strong_lines(lines)
    return {'route':'EXTERNAL_SEARCH_FIRST' if len(strong)>=3 and size_candidates(' '.join(strong)) else 'QWEN_REQUIRED','verified':False}

def fuse(fields, lines):
    evidence=strong_lines(lines)
    joined=normalize(' '.join(evidence))
    tokens=' '.join(re.findall(r'\w+',unicodedata.normalize('NFKC',' '.join(evidence)).casefold()))
    result={}
    for key,value in fields.items():
        needle=normalize(value)
        phrase=' '.join(re.findall(r'\w+',unicodedata.normalize('NFKC',str(value or '')).casefold()))
        supported=bool(phrase and re.search(r'(?<!\w)'+re.escape(phrase)+r'(?!\w)',tokens))
        similar=max((SequenceMatcher(None,needle,normalize(w)).ratio() for line in evidence for w in line.split()),default=0) if len(needle)>=4 else 0
        result[key]={'value':value,'status':'OCR_CORROBORATED' if supported else 'UNSUPPORTED','source':'QWEN','approximate_match':round(similar,3) if key=='brand' else None}
    sizes=size_candidates(' '.join(evidence))
    expected_sizes={canonical_size(s) for s in size_candidates(str(fields.get('size') or ''))}
    observed_sizes={canonical_size(s) for s in sizes}
    # Metric amounts in dual-unit labels are compared independently of fl-oz text.
    metric=lambda values:{s for s in values if s.endswith(('ml','g'))}
    if metric(expected_sizes) and metric(observed_sizes):
        expected_sizes,observed_sizes=metric(expected_sizes),metric(observed_sizes)
    conflict=bool(expected_sizes and observed_sizes and not observed_sizes.issubset(expected_sizes))
    if 'size' in result and expected_sizes and expected_sizes.issubset(observed_sizes):
        result['size']['status']='OCR_CORROBORATED'
    return {'fields':result,'ocr_size_candidates':sizes,'size_conflict':conflict,'status':'REVIEW_REQUIRED','verified':False,'routing':route(lines),'numeric_review_candidates':re.findall(r'\b\d{2,5}\b',' '.join(evidence))}

def read_ocr(path, reader):
    lines=[]
    for page in reader.predict(str(path)):
        data=page.json
        data=data.get('res',data)
        for text,score in zip(data.get('rec_texts',[]),data.get('rec_scores',[])):
            lines.append({'text':str(text),'score':float(score)})
    return lines
