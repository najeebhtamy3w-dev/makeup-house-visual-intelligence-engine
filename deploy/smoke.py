#!/usr/bin/env python3
"""Authenticated health smoke check; never prints the token or claims model readiness."""
import argparse
import json
import sys
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
try:
    from .configuration import read_config
except ImportError:
    from configuration import read_config

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env', required=True)
    parser.add_argument('--url', help='Default: configured HTTPS domain; HTTP permitted only for loopback')
    args = parser.parse_args()
    try:
        config = read_config(args.env)
        base = args.url or 'https://' + config['MHVIE_DOMAIN']
        url = urlsplit(base)
        if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('','/'):
            raise ValueError('INVALID_SMOKE_URL')
        if url.scheme != 'https' and url.hostname not in ('localhost','127.0.0.1','::1'):
            raise ValueError('SMOKE_HTTPS_REQUIRED')
        request = Request(base.rstrip('/') + '/v1/health', headers={'Authorization':'Bearer ' + config['MHVIE_TOKEN']})
        with build_opener(NoRedirect()).open(request, timeout=15) as response:
            data = response.read(100001)
        if len(data) > 100000:
            raise ValueError('HEALTH_RESPONSE_LIMIT')
        health = json.loads(data)
        if health.get('status') != 'API_AVAILABLE':
            raise ValueError('API_HEALTH_NOT_READY')
        print('AUTHENTICATED_API_REACHABLE; model readiness remains ' + str(health.get('model_readiness','UNKNOWN')))
        return 0
    except Exception as error:
        print('HEALTH_CHECK_FAILED: ' + (str(error) if isinstance(error, ValueError) else type(error).__name__), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
