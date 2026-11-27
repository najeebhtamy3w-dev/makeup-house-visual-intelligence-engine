"""Corroborate hypotheses without treating OCR agreement as verified SKU."""
import re
import unicodedata

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
