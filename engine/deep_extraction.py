"""Extract public image candidates; no network access or SKU approval."""
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit
import json

def normalize(page, raw):
    try:
        p = urlsplit(urljoin(page, raw.strip()))
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password or p.port not in (None, 443):
            return None
        return urlunsplit(('https', p.netloc, p.path, p.query, ''))
    except (ValueError, AttributeError):
        return None

class Extractor(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.items = {}
        self.ld = None

    def add(self, raw, kind, width=0):
        if not isinstance(raw, str) or not raw.strip():
            return
        url = normalize(self.page, raw)
        if not url:
            return
        row = self.items.setdefault(url, {'url': url, 'source': self.page,
            'methods': [], 'declared_width': 0, 'rights': 'RIGHTS_UNVERIFIED',
            'status': 'NEEDS_MANUAL_REVIEW'})
        if kind not in row['methods']:
            row['methods'].append(kind)
        row['declared_width'] = max(width, row['declared_width'])

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta' and (a.get('property') or a.get('name')) in ('og:image','og:image:secure_url','twitter:image'):
            self.add(a.get('content'), 'metadata')
        if tag in ('img', 'source'):
            for key in ('src','data-src','data-original','data-zoom-image'):
                self.add(a.get(key), 'html')
            for key in ('srcset','data-srcset'):
                for entry in (a.get(key) or '').split(','):
                    parts = entry.strip().split()
                    if parts:
                        width = int(parts[1][:-1]) if len(parts)>1 and parts[1].endswith('w') and parts[1][:-1].isdigit() else 0
                        self.add(parts[0], 'srcset', width)
        if tag == 'script' and a.get('type') == 'application/ld+json':
            self.ld = []

    def handle_data(self, data):
        if self.ld is not None:
            self.ld.append(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self.ld is not None:
            raw = ''.join(self.ld)
            self.ld = None
            try:
                self.walk(json.loads(raw))
            except (ValueError, RecursionError):
                pass

    def walk(self, node):
        if isinstance(node, list):
            for x in node:
                self.walk(x)
        elif isinstance(node, dict):
            types = node.get('@type', [])
            if types == 'Product' or isinstance(types, list) and 'Product' in types:
                self.images(node.get('image'))
            for x in node.values():
                if isinstance(x, (dict, list)):
                    self.walk(x)

    def images(self, node):
        if isinstance(node, str):
            self.add(node, 'product_jsonld')
        elif isinstance(node, list):
            for x in node:
                self.images(x)
        elif isinstance(node, dict):
            self.add(node.get('contentUrl') or node.get('url'), 'product_jsonld')

def extract(page, html, limit=30):
    if not 1 <= limit <= 200:
        raise ValueError('invalid candidate limit')
    parser = Extractor(page)
    parser.feed(html)
    def rank(row):
        methods = row['methods']
        return ('product_jsonld' in methods, row['declared_width'], 'metadata' in methods)
    return sorted(parser.items.values(), key=rank, reverse=True)[:limit]
