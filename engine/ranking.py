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
    return sorted(eligible,key=lambda x:-x['technical_score'])
