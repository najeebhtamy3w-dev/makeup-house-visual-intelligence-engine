"""Exact OCR corroboration of a unique catalog hypothesis; never verification."""
from .identity_fusion import strong_lines, canonical_size, size_candidates
from .sku_evidence import norm, size

def fast_candidate(lines, evidence):
    text=' '+norm(' '.join(strong_lines(lines)))+' '
    sizes={size(canonical_size(s)) for s in size_candidates(text)}
    sizes.discard(None)
    if len(sizes)!=1:
        return None
    candidates={}
    for item in evidence:
        fields=item.get('fields',{})
        if not all(isinstance(fields.get(k),str) and fields[k].strip() for k in ('brand','name','size')):
            continue
        if size(fields['size']) not in sizes:
            continue
        if not all(' '+norm(fields[k])+' ' in text for k in ('brand','name')):
            continue
        if any(fields.get(k) and ' '+norm(fields[k])+' ' not in text for k in ('variant','shade','concentration')):
            continue
        key=tuple(norm(fields.get(k)) for k in ('brand','name','size','variant','shade','concentration','gtin'))
        candidates[key]=fields
    if len(candidates)!=1:
        return None
    fields=next(iter(candidates.values()))
    return {k:fields[k] for k in ('brand','name','size','variant','shade','concentration') if fields.get(k)}
