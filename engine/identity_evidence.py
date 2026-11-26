from .identity import valid_gtin
from .multimodal import search_name

def collect(image, fields, barcode=None, ocr=None, multimodal=None):
    result={'fields':dict(fields),'diagnostics':{},'hypothesis':None,'query':'','commercial_approved':False}
    d=result['diagnostics']
    for key,reader in [('barcode',barcode),('ocr',ocr)]:
        if reader is None:
            d[key]={'status':'NOT_CONFIGURED'}
            continue
        try:
            rows=reader.read(image)
            d[key]={'status':'EXECUTED','rows':rows}
            if key=='barcode':
                codes={x['text'].zfill(14) for x in rows if valid_gtin(x['text'])}
                existing=fields.get('barcode')
                if len(codes)>1 or (codes and existing and existing.zfill(14) not in codes):
                    d[key]['status']='CONFLICT'
                elif len(codes)==1 and not existing:
                    result['fields']['barcode']=next(iter(codes))
        except Exception as exc:
            d[key]={'status':'FAILED','error':str(exc)}
    if multimodal is not None:
        try:
            result['hypothesis']=multimodal.identify(image)
            result['query']=search_name(result['hypothesis']['fields'])
        except Exception as exc:
            d['multimodal']={'status':'FAILED','error':str(exc)}
    if d['barcode']['status']=='CONFLICT':
        result['status']='IDENTITY_CONFLICT'
    else:
        result['status']='REVIEW_REQUIRED'
    return result
