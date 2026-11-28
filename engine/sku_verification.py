from .identity import assess, valid_gtin

def verify(reference_image,candidate_image,reference_fields,candidate_fields,barcode_reader=None,ocr_reader=None,encoder=None):
    reference=dict(reference_fields)
    candidate=dict(candidate_fields)
    diagnostics={}
    for name,image,fields in [('reference',reference_image,reference),('candidate',candidate_image,candidate)]:
        if barcode_reader is not None:
            try:
                rows=barcode_reader.read(image)
                codes={x['text'].zfill(14) for x in rows if valid_gtin(x['text'])}
                diagnostics[name+'_barcodes']=rows
                if len(codes)==1 and not fields.get('barcode'):
                    fields['barcode']=next(iter(codes))
                elif len(codes)>1 or (codes and fields.get('barcode') and fields['barcode'].zfill(14) not in codes):
                    diagnostics[name+'_barcode_conflict']=True
            except Exception as exc:
                diagnostics[name+'_barcode_error']=str(exc)
        else:
            diagnostics[name+'_barcode_status']='NOT_CONFIGURED'
        if ocr_reader is not None:
            try:
                diagnostics[name+'_ocr']=ocr_reader.read(image)
            except Exception as exc:
                diagnostics[name+'_ocr_error']=str(exc)
        else:
            diagnostics[name+'_ocr_status']='NOT_CONFIGURED'
    similarity=None
    if encoder is not None:
        try:
            similarity=encoder.similarity(reference_image,candidate_image)
        except Exception as exc:
            diagnostics['encoder_error']=str(exc)
    else:
        diagnostics['encoder_status']='NOT_CONFIGURED'
    result=assess(reference,candidate,similarity)
    if any(k.endswith('_barcode_conflict') for k in diagnostics):
        result['status']='SKU_CONFLICT'
        result['conflicts'].append('image_barcode')
    result['diagnostics']=diagnostics
    return result
