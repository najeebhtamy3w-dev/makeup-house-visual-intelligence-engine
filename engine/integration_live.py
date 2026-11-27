"""Live acceptance; requires operator-configured SearXNG and source allowlist."""
import argparse
import json
import time
from pathlib import Path
from .priority_discovery import priority_discover as discover
from .search_discovery import SearxDiscovery

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--endpoint',required=True)
    p.add_argument('--host',action='append',required=True)
    p.add_argument('--output',default='results-integration')
    p.add_argument('--clip-weights')
    p.add_argument('--aesthetic-weights')
    p.add_argument('--aesthetic-sha256')
    p.add_argument('--reference',type=Path)
    p.add_argument('--expected-fields',type=Path)
    a=p.parse_args()
    if bool(a.reference)!=bool(a.expected_fields): p.error('reference and expected fields must be supplied together')
    if a.reference and not a.clip_weights: p.error('reference requires CLIP weights')
    evaluator=None
    if a.clip_weights:
        from .visual_evaluator import LocalClip,VisualEvaluator
        from .aesthetic import AestheticPredictor
        encoder=LocalClip(a.clip_weights)
        head=AestheticPredictor(encoder,a.aesthetic_weights,a.aesthetic_sha256) if a.aesthetic_weights else None
        evaluator=VisualEvaluator(encoder,head)
    root=Path(a.output)
    root.mkdir(parents=True,exist_ok=True)
    search=SearxDiscovery(a.endpoint)
    queries=['CeraVe Hydrating Facial Cleanser','Pura D\'or Vitamin C Serum','Maybelline Sky High Mascara']
    expected=None
    if a.reference:
        from .multimodal import search_name
        expected=json.loads(a.expected_fields.read_text(encoding='utf-8'))
        query=search_name(expected)
        if not query or not expected.get('name'): p.error('reference product name required')
        queries=[query[:240]]
        evaluator=evaluator.for_reference(a.reference)
    reports=[]
    for i,q in enumerate(queries):
        start=time.monotonic()
        try:
            result=discover(q,search,a.host,root/str(i),max_pages=5,max_images=20,visual_evaluator=evaluator,expected_fields=expected)
        except Exception as exc:
            result={'query':q,'status':'FAILED','error':type(exc).__name__,'candidates':[]}
        result['visual_evaluated_count']=sum(c.get('visual_evidence',{}).get('classification_cosine') is not None for c in result['candidates'])
        result['aesthetic_evaluated_count']=sum(c.get('visual_evidence',{}).get('aesthetic_normalized') is not None for c in result['candidates'])
        result['reference_similarity_count']=sum(c.get('visual_evidence',{}).get('similarity_cosine') is not None for c in result['candidates'])
        result['reference_mode']='operator_labeled' if a.reference else 'none'
        result['elapsed_seconds']=time.monotonic()-start
        reports.append(result)
        (root/'report.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
        print(json.dumps({'query':q,'status':result['status'],'count':len(result['candidates'])}),flush=True)
    (root/'report.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
    if not all(r['candidates'] and not r.get('publication_allowed',False) for r in reports):
        raise SystemExit('LIVE_DISCOVERY_GATE_FAILED')
    if evaluator is not None and not all(r['visual_evaluated_count']==len(r['candidates']) for r in reports):
        raise SystemExit('LIVE_VISUAL_GATE_FAILED')
    if a.reference and not all(r['reference_similarity_count']==len(r['candidates']) for r in reports):
        raise SystemExit('REFERENCE_SIMILARITY_GATE_FAILED')
    if a.aesthetic_weights and not all(r['aesthetic_evaluated_count']==len(r['candidates']) for r in reports):
        raise SystemExit('LIVE_AESTHETIC_GATE_FAILED')

if __name__=='__main__':
    main()
