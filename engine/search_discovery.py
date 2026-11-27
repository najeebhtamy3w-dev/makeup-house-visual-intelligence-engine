"""Explicit opt-in SearXNG discovery. Search results are unverified evidence."""
import json
from urllib.parse import urlencode, urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None

class SearxDiscovery:
    def __init__(self, endpoint, timeout=12):
        u=urlsplit(endpoint)
        if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or u.query or u.fragment:
            raise ValueError('INVALID_SEARCH_ENDPOINT')
        if u.scheme=='http' and u.hostname not in ('localhost','127.0.0.1','::1'):
            raise ValueError('HTTPS_REQUIRED')
        self.endpoint=endpoint.rstrip('/')+'/search'
        self.timeout=timeout
    def __call__(self, query):
        if not query.strip():
            return []
        url=self.endpoint+'?'+urlencode({'q':query[:240],'format':'json','categories':'general'})
        with build_opener(NoRedirect()).open(Request(url,headers={'Accept':'application/json'}),timeout=self.timeout) as response:
            raw=response.read(1000001)
        if len(raw)>1000000:
            raise ValueError('SEARCH_RESPONSE_LIMIT')
        return parse_results(json.loads(raw))

def parse_results(data):
    results=[]
    seen=set()
    for row in data.get('results',[])[:100]:
        if not isinstance(row,dict): continue
        url=row.get('url','')
        if not isinstance(url,str): continue
        u=urlsplit(url)
        if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or url in seen: continue
        seen.add(url)
        results.append({'url':url,'title':str(row.get('title',''))[:300],'snippet':str(row.get('content',''))[:500],'verified':False})
        if len(results)>=10: break
    return results
