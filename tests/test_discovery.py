import unittest
from unittest.mock import patch
from engine.discovery import parse_results, discover

class DiscoveryTests(unittest.TestCase):
    def test_social_filter(self):
        urls=['https://www.instagram.com/p/abc/','https://instagram.com/profile/','https://instagram.com.evil.org/p/abc/','https://www.instagram.com/p/abc/']
        rows=parse_results({'results':[{'url':u} for u in urls]},'instagram')
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['rights'],'RIGHTS_UNVERIFIED')

    def test_failure_is_explicit(self):
        with patch('engine.discovery.urlopen',side_effect=OSError('offline')):
            rows=discover('CeraVe','http://127.0.0.1:8080')
        self.assertEqual([x['status'] for x in rows],['SEARCH_FAILED','SEARCH_FAILED'])

    def test_endpoint_validation(self):
        with self.assertRaises(ValueError):
            discover('CeraVe','http://example.com')
