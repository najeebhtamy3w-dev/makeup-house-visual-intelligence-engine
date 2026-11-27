"""Technical quality ordering, not a learned aesthetic score."""
def rank_candidates(rows):
    eligible=[]
    for row in rows:
        if row.get('status')!='NEEDS_MANUAL_REVIEW':
            continue
        w,h=row.get('width',0),row.get('height',0)
        if min(w,h)<400:
            continue
        resolution=min(min(w,h)/800,1)
        brightness=max(0,1-abs(row.get('brightness',128)-128)/128)
        score=round(0.85*resolution+0.15*brightness,4)
        eligible.append({'sha256':row.get('sha256'),'file':row.get('file'),'url':row.get('url'),'technical_score':score,'aesthetic_status':'NOT_EVALUATED','commercial_approved':False})
        aesthetic=row.get('aesthetic',{})
        item=eligible[-1]
        item['aesthetic_status']=aesthetic.get('status','NOT_EVALUATED')
        item['aesthetic_score']=aesthetic.get('score') if item['aesthetic_status']=='EVALUATED' else None
        item['combined_score']=round(.5*score+.5*item['aesthetic_score'],4) if item['aesthetic_score'] is not None else score
    # Do not compare calibrated and fallback scores as if equivalent.
    return sorted(eligible,key=lambda x:(x['aesthetic_score'] is None,-x['combined_score']))
