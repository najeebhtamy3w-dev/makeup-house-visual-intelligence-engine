"""Conservative candidate-level evidence fusion; never verifies publication."""
import math

def assess_candidate_identity(row):
    visual=row.get('visual_evidence') or {}
    page=row.get('page_sku_evidence') or []
    similarity=visual.get('similarity_cosine')
    strong=isinstance(similarity,(int,float)) and not isinstance(similarity,bool) and math.isfinite(similarity) and similarity>=0.85
    page_match=any(e.get('status')=='CORROBORATED_REVIEW_REQUIRED' for e in page)
    conflict=bool(row.get('page_sku_conflict')) or visual.get('identity_status')=='CONFLICT'
    status='CONFLICT' if conflict else 'CORROBORATED_REVIEW_REQUIRED' if strong and page_match and visual.get('category') in ('packshot','detail','advertising','lifestyle') else 'INSUFFICIENT_EVIDENCE'
    return {'status':status,'page_match':page_match,'visual_similarity_supported':strong,'identity_verified':False,'publication_allowed':False}
