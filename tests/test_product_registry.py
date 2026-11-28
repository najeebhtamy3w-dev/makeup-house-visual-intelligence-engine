import tempfile
import unittest
from pathlib import Path
from engine.product_registry import ProductRegistry
from engine.multi_input import resolve_input

class RegistryTests(unittest.TestCase):
    def test_persistence_and_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'products.sqlite3'
            code='4006381333931'
            fields={'brand':'QV','name':'Cleanser','size':'250g'}
            registry=ProductRegistry(path)
            self.assertEqual(registry.lookup(code),[])
            registry.approve(code,fields,'operator fixture')
            registry=ProductRegistry(path)
            self.assertTrue(registry.lookup('04006381333931')[0]['operator_reviewed'])
            result=resolve_input(code,None,None,registry.lookup,lambda p:self.fail('visual'),lambda q:{'query':q})
            self.assertEqual(result['route'],'BARCODE_REGISTRY')
            self.assertFalse(result['publication_allowed'])
            with self.assertRaises(ValueError): registry.approve(code,dict(fields,size='500g'),'conflict')
            self.assertTrue(registry.revoke(code))
            self.assertEqual(registry.lookup(code),[])
