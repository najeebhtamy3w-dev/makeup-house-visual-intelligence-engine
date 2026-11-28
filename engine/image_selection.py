"""Rank candidates for human review; missing model evidence is explicit."""
import math
CLASSES={'packshot','lifestyle','advertising','detail','texture','swatch','group','logo','unrelated','unknown'}

def score01(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=1:
        return None
    return float(value)

def rank_candidates(rows, purpose='catalog'):
    if purpose not in ('catalog','marketing'): raise ValueError('INVALID_PURPOSE')
    ranked=[]
    for row in rows:
        item=dict(row)
        evidence=row.get('visual_evidence') or {}
        category=evidence.get('category','unknown')
        if category not in CLASSES: category='unknown'
        identity=evidence.get('identity_status','INSUFFICIENT_EVIDENCE')
        aesthetic=score01(evidence.get('aesthetic_normalized'))
        similarity=score01(evidence.get('similarity_normalized'))
        resolution=min(1.0,min(row['width'],row['height'])/1200)
        preferred={'packshot','detail'} if purpose=='catalog' else {'lifestyle','advertising'}
        rejected=identity=='CONFLICT' or category in ('logo','unrelated')
        corroborated=identity=='CORROBORATED_REVIEW_REQUIRED'
        parts={'resolution':resolution,'aesthetic':aesthetic,'similarity':similarity,'purpose_fit':None if category=='unknown' else float(category in preferred)}
        weights={'resolution':.25,'aesthetic':.25,'similarity':.30,'purpose_fit':.20}
        available=sum(weights[k] for k,v in parts.items() if v is not None)
        score=sum(weights[k]*v for k,v in parts.items() if v is not None)
        item['selection']={'purpose':purpose,'category':category,'identity_status':identity,'score':round(score,4),'evidence_coverage':round(available,4),'components':parts,'status':'REJECTED' if rejected else 'REVIEW_REQUIRED','publication_allowed':False}
        item['publication_allowed']=False
        item['identity_verified']=False
        ranked.append((not rejected,corroborated,not bool(row.get('possible_duplicate_of')),score,item))
    ranked.sort(key=lambda x:x[:4],reverse=True)
    return [x[4] for x in ranked]
