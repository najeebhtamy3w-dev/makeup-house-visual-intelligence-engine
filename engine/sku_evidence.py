"""Compare structured SKU evidence without promoting matches to verified identity."""
import re
import unicodedata
from decimal import Decimal
from .barcode_priority import canonical_gtin

_DIGITS=str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹','01234567890123456789')

def norm(value):
    return ' '.join(re.findall(r'\w+',unicodedata.normalize('NFKC',str(value or '')).casefold()))

def size(value):
    text=str(value or '').translate(_DIGITS).casefold()
    for source,target in (('كجم','kg'),('كيلوغرام','kg'),('غرام','g'),('جم','g'),('مل','ml'),('لتر','l')):
        text=text.replace(source,target)
    match=re.fullmatch(r'\s*(\d+(?:[.,]\d+)?)\s*(ml|l|g|kg)\s*',text)
    if not match: return None
    n=Decimal(match[1].replace(',','.'))
    if n<=0: return None
    unit=match[2]
    return (n*(1000 if unit in ('l','kg') else 1),'ml' if unit in ('ml','l') else 'g')

def compare(expected, observed):
    matches=[]; conflicts=[]; unknown=[]; invalid=[]
    for field in ('brand','name','variant','size','gtin','shade','concentration','formula'):
        a=expected.get(field) or (expected.get('barcode') if field=='gtin' else None)
        b=observed.get(field) or (observed.get('barcode') if field=='gtin' else None)
        if not a or not b:
            unknown.append(field)
            continue
        if field=='gtin':
            a,b=canonical_gtin(a),canonical_gtin(b)
            if a is None or b is None:
                invalid.append(field)
                unknown.append(field)
                continue
        elif field=='size':
            a,b=size(a),size(b)
            if a is None or b is None:
                unknown.append(field)
                continue
        else:
            a,b=norm(a),norm(b)
        (matches if a==b else conflicts).append(field)
    required={'brand','name','size'} | {k for k in ('variant','shade','concentration','formula','gtin') if expected.get(k)}
    if expected.get('barcode'): required.add('gtin')
    status='CONFLICT' if conflicts else 'CORROBORATED_REVIEW_REQUIRED' if not invalid and required.issubset(matches) else 'INSUFFICIENT_EVIDENCE'
    return {'status':status,'matches':matches,'conflicts':conflicts,'unknown':unknown,'invalid':invalid,'verified':False,'publication_allowed':False}
