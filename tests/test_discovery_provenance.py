import unittest
from unittest.mock import patch
from engine.priority_discovery import priority_discover

class ProvenanceTests(unittest.TestCase):
    @patch('engine.priority_discovery.discover')
    def test_duplicate_preserves_both_sources(self, discover):
        def row(source):
            return {'sha256':'same','source':source,'url':source+'/image.jpg','width':800,'height':800}
        discover.side_effect=[
            {'status':'REVIEW_REQUIRED','errors':[],'candidates':[row('https://www.instagram.com/p/test/')]},
            {'status':'REVIEW_REQUIRED','errors':[],'candidates':[row('https://example.org/product')]}]
        def search(q):
            return [{'url':'https://www.instagram.com/p/test/'}] if 'site:instagram.com' in q else [{'url':'https://example.org/product'}]
        result=priority_discover('QV cleanser',search,['instagram.com','example.org'],'/tmp/unused')
        self.assertEqual(len(result['candidates']),1)
        self.assertEqual([e['stage'] for e in result['candidates'][0]['source_evidence']],['instagram','web'])
        self.assertFalse(result['publication_allowed'])
        self.assertTrue(result['creative_fallback_suggested'])
