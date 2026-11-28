import unittest
import json
from unittest.mock import patch, MagicMock
from engine.search_discovery import SearxDiscovery, parse_results

class SearchTests(unittest.TestCase):
    def test_filter(self):
        rows=[{'url':'https://example.org/product','title':'Product'}, {'url':'https://example.org/product'}, {'url':'file:///etc/passwd'}]
        result=parse_results({'results':rows})
        self.assertEqual(len(result),1)
        self.assertFalse(result[0]['verified'])
    def test_endpoint(self):
        with self.assertRaises(ValueError):
            SearxDiscovery('http://example.org')
    @patch('engine.search_discovery.build_opener')
    def test_request(self, opener):
        response=opener.return_value.open.return_value.__enter__.return_value
        response.read.return_value=json.dumps({'results':[{'url':'https://example.org/item'}]}).encode()
        self.assertEqual(len(SearxDiscovery('http://127.0.0.1:8080')('Anua 30 ml')),1)
        request=opener.return_value.open.call_args.args[0]
        self.assertIn('q=Anua+30+ml',request.full_url)
