import unittest
from engine.catalog_evidence import extract_catalog,collect_catalog
class CatalogTests(unittest.TestCase):
    def test_product_graph(self):
        html='<script type="application/ld+json">{"@graph":[{"@type":"Product","name":"Wash","brand":{"name":"QV"},"size":"500 g","gtin13":"1234567890123"}]}</script>'
        rows=extract_catalog('https://example.com/p',html)
        self.assertEqual(rows[0]['fields']['brand'],'QV')
        self.assertEqual(rows[0]['fields']['size'],'500 g')
        self.assertFalse(rows[0]['verified'])
    def test_invalid(self):
        self.assertEqual(extract_catalog('x','<script type="application/ld+json">bad</script>'),[])
    def test_failure(self):
        class Failed:
            def fetch(self,*args): raise TimeoutError()
        result=collect_catalog([{'url':'https://example.com'}],Failed())
        self.assertEqual(result['evidence'],[])
        self.assertEqual(result['errors'][0]['error'],'TimeoutError')
