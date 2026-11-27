"""Extract source-attributed product hypotheses from JSON-LD, never verified facts."""
import json
from html.parser import HTMLParser

class CatalogParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active=False
        self.parts=[]
        self.products=[]
    def handle_starttag(self,tag,attrs):
        if tag=='script' and dict(attrs).get('type')=='application/ld+json':
            self.active=True
            self.parts=[]
    def handle_data(self,data):
        if self.active: self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self.active:
            self.active=False
            try: self.walk(json.loads(''.join(self.parts)))
            except (ValueError,RecursionError): pass
    def walk(self,node):
        if isinstance(node,list):
            for item in node: self.walk(item)
        elif isinstance(node,dict):
            types=node.get('@type',[])
            if types=='Product' or isinstance(types,list) and 'Product' in types:
                brand=node.get('brand')
                if isinstance(brand,dict): brand=brand.get('name')
                fields={'brand':brand,'name':node.get('name'),'size':node.get('size'),'variant':node.get('color'),'gtin':next((node[k] for k in ('gtin14','gtin13','gtin12','gtin8','gtin') if isinstance(node.get(k),str)),None)}
                fields={k:v[:300] for k,v in fields.items() if isinstance(v,str) and v.strip()}
                if fields and len(self.products)<20: self.products.append(fields)
            for value in node.values():
                if isinstance(value,(dict,list)): self.walk(value)

def extract_catalog(source,html):
    if len(html)>2000000: raise ValueError('HTML_LIMIT')
    parser=CatalogParser()
    parser.feed(html)
    return [{'source':source,'fields':fields,'verified':False} for fields in parser.products]

def collect_catalog(hits,downloader,max_pages=3):
    if not 1<=max_pages<=10: raise ValueError('PAGE_LIMIT')
    evidence=[]; errors=[]
    for hit in hits[:max_pages]:
        if not isinstance(hit,dict) or not isinstance(hit.get('url'),str): continue
        try:
            raw,_,url=downloader.fetch(hit['url'],2000000,'text/html')
            evidence.extend(extract_catalog(url,raw.decode('utf-8','replace')))
        except Exception as exc:
            errors.append({'source':hit['url'],'error':type(exc).__name__})
    return {'evidence':evidence[:20],'errors':errors}
