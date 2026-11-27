"""Compare structured SKU evidence without promoting matches to verified identity."""
import re
import unicodedata
from decimal import Decimal

def norm(value):
    return ' '.join(re.findall(r'\w+',unicodedata.normalize('NFKC',str(value or '')).casefold()))

def size(value):
    match=re.fullmatch(r'\s*(\d+(?:[.,]\d+)?)\s*(ml|l|g|kg)\s*',str(value or '').casefold())
    if not match: return None
    n=Decimal(match[1].replace(',','.'))
    unit=match[2]
    return (n*(1000 if unit in ('l','kg') else 1),'ml' if unit in ('ml','l') else 'g')

def compare(expected, observed):
    matches=[]; conflicts=[]; unknown=[]
    for field in ('brand','name','variant','size','gtin'):
        a,b=expected.get(field),observed.get(field)
        if not a or not b:
            unknown.append(field)
            continue
        if field=='size':
            a,b=size(a),size(b)
            if a is None or b is None:
                unknown.append(field)
                continue
        else:
            a,b=norm(a),norm(b)
        (matches if a==b else conflicts).append(field)
    status='CONFLICT' if conflicts else 'CORROBORATED_REVIEW_REQUIRED' if {'brand','name','size'}.issubset(matches) else 'INSUFFICIENT_EVIDENCE'
    return {'status':status,'matches':matches,'conflicts':conflicts,'unknown':unknown,'verified':False,'publication_allowed':False}
