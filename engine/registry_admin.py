import argparse
import json
from pathlib import Path
from .product_registry import ProductRegistry

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',required=True)
    p.add_argument('action',choices=['approve','lookup','revoke'])
    p.add_argument('barcode')
    p.add_argument('--fields')
    p.add_argument('--source')
    a=p.parse_args()
    root=Path(a.data)
    root.mkdir(parents=True,exist_ok=True)
    registry=ProductRegistry(root/'products.sqlite3')
    if a.action=='approve':
        if not a.fields or not a.source: p.error('approve requires --fields JSON and --source')
        registry.approve(a.barcode,json.loads(a.fields),a.source)
        result=registry.lookup(a.barcode)
    elif a.action=='revoke': result={'revoked':registry.revoke(a.barcode)}
    else: result=registry.lookup(a.barcode)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__': main()
