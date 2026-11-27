"""Corroborate hypotheses without treating OCR agreement as verified SKU."""
import re
import unicodedata
from difflib import SequenceMatcher

def size_candidates(text):
    text=unicodedata.normalize('NFKC',text).casefold()
    return sorted(set(re.findall(r'\b\d+(?:[.,]\d+)?\s*(?:m\s*[l1i]|k\s*g|g|oz)\b',text)))

def canonical_size(text):
    return re.sub(r'm[1i]

def normalize(value):
    return re.sub(r'[^\w]+', '', unicodedata.normalize('NFKC', value).casefold())

def fuse(fields, lines):
    evidence = []
    for line in lines:
        if isinstance(line.get('text'), str) and float(line.get('score', 0)) >= 0.8:
            evidence.append(line['text'])
    joined = normalize(' '.join(evidence))
    result = {}
    for key, value in fields.items():
        needle = normalize(value or '')
        supported = len(needle) >= 3 and needle in joined
        similar = max((SequenceMatcher(None,needle,normalize(w)).ratio() for line in evidence for w in line.split()),default=0) if len(needle)>=4 else 0
        result[key] = {'value': value, 'status': 'OCR_CORROBORATED' if supported else 'UNSUPPORTED', 'source': 'QWEN', 'approximate_match': round(similar,3) if key=='brand' else None}
    sizes = size_candidates(' '.join(evidence))
    conflict = bool(fields.get('size') and sizes and canonical_size(fields['size']) not in {canonical_size(s) for s in sizes})
    return {'fields': result, 'ocr_size_candidates': sizes, 'size_conflict': conflict, 'status': 'REVIEW_REQUIRED', 'verified': False, 'routing': route(lines), 'numeric_review_candidates': re.findall(r'\b\d{2,5}\b', ' '.join(evidence))}

def read_ocr(path, reader):
    lines = []
    for page in reader.predict(str(path)):
        data = page.json
        data = data.get('res', data)
        for text, score in zip(data.get('rec_texts', []), data.get('rec_scores', [])):
            lines.append({'text': str(text), 'score': float(score)})
    return lines
, 'ml', normalize(text))

def route(lines):
    # OCR alone cannot establish SKU identity; route weak evidence to visual analysis.
    strong=[x['text'] for x in lines if x.get('score',0)>=0.8 and x.get('text')]
    return {'route':'EXTERNAL_SEARCH_FIRST' if len(strong)>=3 and size_candidates(' '.join(strong)) else 'QWEN_REQUIRED','verified':False}


def normalize(value):
    return re.sub(r'[^\w]+', '', unicodedata.normalize('NFKC', value).casefold())

def fuse(fields, lines):
    evidence = []
    for line in lines:
        if isinstance(line.get('text'), str) and float(line.get('score', 0)) >= 0.8:
            evidence.append(line['text'])
    joined = normalize(' '.join(evidence))
    result = {}
    for key, value in fields.items():
        needle = normalize(value)
        supported = len(needle) >= 3 and needle in joined
        result[key] = {'value': value, 'status': 'OCR_CORROBORATED' if supported else 'UNSUPPORTED', 'source': 'QWEN'}
    sizes = sorted(set(re.findall(r'\b\d+(?:[.,]\d+)?\s*(?:ml|kg|g|oz)\b', ' '.join(evidence), re.I)))
    conflict = bool(fields.get('size') and sizes and normalize(fields['size']) not in {normalize(s) for s in sizes})
    return {'fields': result, 'ocr_size_candidates': sizes, 'size_conflict': conflict, 'status': 'REVIEW_REQUIRED', 'verified': False}

def read_ocr(path, reader):
    lines = []
    for page in reader.predict(str(path)):
        data = page.json
        data = data.get('res', data)
        for text, score in zip(data.get('rec_texts', []), data.get('rec_scores', [])):
            lines.append({'text': str(text), 'score': float(score)})
    return lines
