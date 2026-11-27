"""Evaluate fixed human-labeled scores; never tune on the acceptance split."""
import json,argparse
def evaluate(rows,threshold):
    accepted=[r for r in rows if r['margin']>=threshold]
    correct=sum(max(r['scores'],key=r['scores'].get)==r['label'] for r in accepted)
    return {'threshold':threshold,'total':len(rows),'accepted':len(accepted),'correct':correct,'coverage':len(accepted)/max(1,len(rows)),'selective_accuracy':correct/max(1,len(accepted))}
def main():
    p=argparse.ArgumentParser()
    p.add_argument('labels')
    a=p.parse_args()
    rows=json.load(open(a.labels,encoding='utf-8'))
    if len({r['sha256'] for r in rows})!=len(rows): raise ValueError('DUPLICATE_IMAGE')
    print(json.dumps([evaluate(rows,t) for t in (0,.003,.005,.008,.01,.015,.02)],indent=2))
if __name__=='__main__': main()
