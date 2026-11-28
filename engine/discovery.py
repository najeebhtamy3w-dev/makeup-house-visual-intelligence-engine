"""Search indexed public product pages via an operator-configured SearXNG."""
import json
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

def parse_results(data, scope):
    rows = []
    seen = set()
    for item in data.get('results', []):
        url = item.get('url', '')
        try:
            p = urlsplit(url)
            if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None,443):
                continue
        except ValueError:
            continue
        social = p.hostname == 'instagram.com' or p.hostname.endswith('.instagram.com')
        if scope == 'instagram' and (not social or not p.path.startswith(('/p/','/reel/'))):
            continue
        if url in seen:
            continue
        seen.add(url)
        rows.append(dict(url=url,title=item.get('title',''),engine=item.get('engine',''),scope=scope,rights='RIGHTS_UNVERIFIED'))
    return rows

def discover(product, endpoint, limit=20):
    if not product.strip() or not 1 <= limit <= 100:
        raise ValueError('INVALID_SEARCH_INPUT')
    # Endpoint is trusted deployment configuration, never a product/user field.
    p = urlsplit(endpoint)
    if p.scheme != 'https' and not (p.scheme == 'http' and p.hostname in ('localhost','127.0.0.1')):
        raise ValueError('INVALID_SEARCH_ENDPOINT')
    report = []
    for scope in ('instagram','web'):
        query = ('site:instagram.com ' if scope == 'instagram' else '') + product
        try:
            url = endpoint.rstrip('/') + '/search?' + urlencode(dict(q=query,format='json',categories='general'))
            with urlopen(Request(url,headers={'User-Agent':'MH-VIE/0.6'}),timeout=30) as response:
                raw = response.read(2000001)
                if len(raw)>2000000:
                    raise ValueError('SEARCH_RESPONSE_LIMIT')
                data = json.loads(raw)
            hits = parse_results(data,scope)[:limit]
            report.append(dict(scope=scope,status='RESULTS' if hits else 'NO_HITS_OR_ENGINE_FAILURE',hits=hits,engine_errors=data.get('unresponsive_engines',[])))
        except Exception as exc:
            report.append(dict(scope=scope,status='SEARCH_FAILED',hits=[],error=str(exc)))
    return report
