"""Conservative candidate-level evidence fusion; never verifies publication."""
import math

def assess_candidate_identity(row):
    visual=row.get('visual_evidence') or {}
    page=row.get('page_sku_evidence') or []
    similarity=visual.get('similarity_cosine')
    strong=isinstance(similarity,(int,float)) and not isinstance(similarity,bool) and math.isfinite(similarity) and 0.85<=similarity<=1
    page_match=any(e.get('status')=='CORROBORATED_REVIEW_REQUIRED' for e in page)
    ocr=row.get('candidate_ocr') or {}
    text_match=bool(ocr.get('brand_supported') and ocr.get('size_supported') and ocr.get('required_text_supported'))
    image_match=text_match or ocr.get('gtin_supported') is True
    conflict=bool(row.get('page_sku_conflict')) or visual.get('identity_status')=='CONFLICT' or bool(ocr.get('size_review_required')) or bool(ocr.get('gtin_conflict'))
    status='CONFLICT' if conflict else 'CORROBORATED_REVIEW_REQUIRED' if strong and image_match and visual.get('category') in ('packshot','detail','advertising','lifestyle') else 'INSUFFICIENT_EVIDENCE'
    return {'status':status,'page_match':page_match,'candidate_text_match':text_match,'visual_similarity_supported':strong,'identity_verified':False,'publication_allowed':False}
