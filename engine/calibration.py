"""Evaluate fixed human-labeled scores; never tune on the acceptance split."""
import json,argparse
def evaluate(rows,threshold):
    accepted=[r for r in rows if r['margin']>=threshold]
    correct=sum(max(r['scores'],key=r['scores'].get)==r['label'] for r in accepted)
    classes=sorted(set().union(*(r['scores'].keys() for r in rows)))
    per_class={}
    for label in classes:
        actual=[r for r in rows if r['label']==label]
        predicted=[r for r in accepted if max(r['scores'],key=r['scores'].get)==label]
        tp=sum(r['label']==label for r in predicted)
        per_class[label]={'support':len(actual),'predicted':len(predicted),'precision':tp/len(predicted) if predicted else None,'recall':tp/len(actual) if actual else None}
    return {'per_class':per_class,'missing_classes':[k for k,v in per_class.items() if not v['support']],'threshold':threshold,'total':len(rows),'accepted':len(accepted),'correct':correct,'coverage':len(accepted)/max(1,len(rows)),'selective_accuracy':correct/max(1,len(accepted))}
def main():
    p=argparse.ArgumentParser()
    p.add_argument('labels')
    a=p.parse_args()
    rows=json.load(open(a.labels,encoding='utf-8'))
    if len({r['sha256'] for r in rows})!=len(rows): raise ValueError('DUPLICATE_IMAGE')
    print(json.dumps([evaluate(rows,t) for t in (0,.003,.005,.008,.01,.015,.02)],indent=2))
if __name__=='__main__': main()
