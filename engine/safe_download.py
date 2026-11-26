"""Bounded HTTPS retrieval. All redirects are independently validated."""
import hashlib
import http.client
import ipaddress
import io
import socket
import ssl
import warnings
from urllib.parse import urlsplit, urljoin

class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout):
        super().__init__(host, 443, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise

def validate_url(url, allowed_hosts):
    p = urlsplit(url)
    host = p.hostname
    if p.scheme != 'https' or not host or p.username or p.password or p.port not in (None, 443):
        raise ValueError('UNSAFE_URL')
    if not any(host == d or host.endswith('.' + d) for d in allowed_hosts):
        raise ValueError('HOST_NOT_ALLOWED')
    return p

def public_address(host):
    addresses = {x[4][0] for x in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(x).is_global or ipaddress.ip_address(x).is_multicast for x in addresses):
        raise ValueError('NON_PUBLIC_ADDRESS')
    return sorted(addresses)[0]

class Downloader:
    def __init__(self, allowed_hosts, timeout=10):
        self.allowed_hosts = tuple(allowed_hosts)
        self.timeout = timeout
        self.blocked = set()

    def fetch(self, url, limit, mime_prefix):
        for _ in range(4):
            p = validate_url(url, self.allowed_hosts)
            if p.hostname in self.blocked:
                raise RuntimeError('SOURCE_BLOCKED')
            conn = PinnedHTTPS(p.hostname, public_address(p.hostname), self.timeout)
            try:
                path = p.path or '/'
                if p.query:
                    path += '?' + p.query
                conn.request('GET', path, headers={'User-Agent':'MH-VIE/0.6', 'Accept-Encoding':'identity'})
                response = conn.getresponse()
                if response.status == 429:
                    self.blocked.add(p.hostname)
                    raise RuntimeError('SOURCE_BLOCKED')
                if response.status in (301,302,303,307,308):
                    location = response.getheader('Location')
                    if not location:
                        raise ValueError('MISSING_REDIRECT')
                    url = urljoin(url, location)
                    continue
                if response.status != 200:
                    raise RuntimeError('HTTP_' + str(response.status))
                mime = (response.getheader('Content-Type') or '').split(';')[0].lower()
                if not mime.startswith(mime_prefix):
                    raise ValueError('INVALID_MIME')
                length = response.getheader('Content-Length')
                if length and int(length) > limit:
                    raise ValueError('SIZE_LIMIT')
                data = response.read(limit + 1)
                if len(data) > limit:
                    raise ValueError('SIZE_LIMIT')
                return data, mime, url
            finally:
                conn.close()
        raise ValueError('REDIRECT_LIMIT')

def inspect_image(data, mime):
    from PIL import Image
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(data)) as im:
            w, h = im.size
            if w*h > 25000000 or min(w,h) < 32:
                raise ValueError('PIXEL_LIMIT')
            if Image.MIME.get(im.format) != mime:
                raise ValueError('MIME_MISMATCH')
            im.verify()
        with Image.open(io.BytesIO(data)) as im:
            im.load()
            return {'width':w,'height':h,'format':im.format,
                    'sha256':hashlib.sha256(data).hexdigest(),
                    'bytes':len(data),'rights':'RIGHTS_UNVERIFIED',
                    'status':'NEEDS_MANUAL_REVIEW'}
