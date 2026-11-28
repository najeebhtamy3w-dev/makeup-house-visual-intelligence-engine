"""Structured identity evidence; no automatic commercial approval."""
import re
import unicodedata
from decimal import Decimal

def normalize(text):
    return ' '.join(re.findall(r'\w+',unicodedata.normalize('NFKC',text).casefold()))

def valid_gtin(code):
    if not isinstance(code,str) or len(code) not in (8,12,13,14) or not code.isascii() or not code.isdigit():
        return False
    return (sum(int(c)*(3 if i%2==0 else 1) for i,c in enumerate(reversed(code[:-1])))+int(code[-1]))%10==0

def canonical_gtin(code):
    return code.zfill(14) if valid_gtin(code) else None

def sizes(text):
    result=set()
    for value,unit in re.findall(r'(\d+(?:[.,]\d+)?)\s*(ml|mL|ML|l|L|g|G|kg|KG|مل|لتر|جم|غرام|كجم)\b',text):
        unit=unit.lower()
        n=Decimal(value.replace(',','.'))
        if unit in ('l','لتر','kg','كجم'):
            n*=1000
        result.add(('volume' if unit in ('ml','مل','l','لتر') else 'mass',n))
    return result

def assess(reference,candidate,visual_similarity=None):
    conflicts=[]
    evidence=[]
    for key in ('brand','variant','concentration','shade'):
        a,b=normalize(reference.get(key) or ''),normalize(candidate.get(key) or '')
        if a and b:
            (evidence if a==b else conflicts).append(key)
    a,b=canonical_gtin(reference.get('barcode')),canonical_gtin(candidate.get('barcode'))
    if a and b:
        (evidence if a==b else conflicts).append('barcode')
    a,b=sizes(reference.get('size') or ''),sizes(candidate.get('size') or '')
    if a and b:
        (evidence if a==b else conflicts).append('size')
    if conflicts:
        status='SKU_CONFLICT'
    elif 'barcode' in evidence:
        status='BARCODE_MATCH_REVIEW_REQUIRED'
    else:
        status='INSUFFICIENT_SKU_EVIDENCE'
    return dict(status=status,evidence=evidence,conflicts=conflicts,
                visual_similarity=visual_similarity,rights='RIGHTS_UNVERIFIED',
                commercial_approved=False)
