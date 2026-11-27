from PIL import Image, ImageOps
from .multimodal import search_name
from .priority_discovery import priority_discover as discover

def read_barcodes(path):
    import zxingcpp
    with Image.open(path) as im:
        if im.width*im.height>25000000: raise ValueError('PIXEL_LIMIT')
        codes=zxingcpp.read_barcodes(ImageOps.exif_transpose(im).convert('RGB'))
    return [{'text':c.text[:200],'format':str(c.format)} for c in codes][:20]

def photo_discovery(path,identity,search,hosts,output,evaluator=None,purpose='catalog',barcode_reader=read_barcodes):
    result=identity(path)
    codes=barcode_reader(path)
    query=search_name(result.get('fields',{}))
    if not query or not result.get('fields',{}).get('name'):
        return {'status':'IDENTITY_REVIEW_REQUIRED','identity':result,'barcodes':codes,'publication_allowed':False}
    if result.get('fusion',{}).get('size_conflict') or any(x.get('comparison',{}).get('status')=='CONFLICT' for x in result.get('sku_evidence',[])):
        return {'status':'IDENTITY_REVIEW_REQUIRED','identity':result,'barcodes':codes,'publication_allowed':False}
    if evaluator is not None and hasattr(evaluator,'for_reference'):
        evaluator=evaluator.for_reference(path)
    found=discover(query[:240],search,hosts,output,visual_evaluator=evaluator,purpose=purpose,expected_fields=result.get('fields',{}))
    return {**found,'identity':result,'barcodes':codes,'query_verified':False,'publication_allowed':False}
