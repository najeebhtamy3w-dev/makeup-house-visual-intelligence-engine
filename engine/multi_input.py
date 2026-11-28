from .barcode_priority import canonical_gtin, matching_evidence
from .catalog_evidence import collect_catalog
from .multimodal import search_name

def resolve_input(barcode, query, path, lookup, visual, named, barcode_reader=None):
    trace=[]
    if barcode and canonical_gtin(barcode) is None: raise ValueError('INVALID_GTIN')
    if barcode and path is not None and barcode_reader is not None:
        from .barcode_priority import valid_gtins
        observed=valid_gtins(barcode_reader(path))
        if observed and observed != [canonical_gtin(barcode)]:
            return {'status':'IDENTITY_REVIEW_REQUIRED','route':'BARCODE_PHOTO_CONFLICT','observed_gtins':observed,'identity_verified':False,'publication_allowed':False}
    if barcode:
        gtin=canonical_gtin(barcode)
        if gtin is None: raise ValueError('INVALID_GTIN')
        try:
            evidence=matching_evidence(lookup(barcode),gtin)
            unique={}
            for item in evidence:
                f=item['fields']
                if all(f.get(k) for k in ('brand','name','size')):
                    key=tuple(str(f.get(k,'')).casefold().strip() for k in ('brand','name','size','variant','shade','concentration'))
                    unique[key]=f
            if len(unique)==1:
                fields=next(iter(unique.values()))
                # A supplied photo or name may contradict the barcode. Require review.
                result=named(search_name(fields))
                if path is not None and 'candidates' in result and not any(c.get('selection',{}).get('status')!='REJECTED' and c.get('status')!='REJECTED' for c in result['candidates']):
                    trace.append('BARCODE_NO_USABLE_IMAGES')
                    fallback=visual(path)
                    return {**fallback,'route':'PHOTO_FALLBACK','route_trace':trace,'barcode_evidence':evidence,'input_consistency':'REVIEW_REQUIRED','identity_verified':False,'publication_allowed':False}
                return {**result,'route':'BARCODE_REGISTRY' if any(e.get('operator_reviewed') for e in evidence) else 'BARCODE_CATALOG','barcode_evidence':evidence,'input_consistency':'REVIEW_REQUIRED' if path or query else 'NOT_CHECKED','identity_verified':False,'publication_allowed':False}
            trace.append('BARCODE_AMBIGUOUS_OR_MISSING')
        except Exception as exc:
            trace.append('BARCODE_'+type(exc).__name__)
    if path is not None:
        result=visual(path)
        route='PHOTO_FALLBACK'
    elif query and query.strip():
        result=named(query.strip())
        route='NAME_FALLBACK'
    else:
        result={'status':'ADDITIONAL_INPUT_REQUIRED'}
        route='REVIEW_REQUIRED'
    return {**result,'route':route,'route_trace':trace,'identity_verified':False,'publication_allowed':False}
