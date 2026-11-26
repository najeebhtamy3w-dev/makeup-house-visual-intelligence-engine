import unittest
from engine.multimodal import parse_identity, search_name

class MultimodalTests(unittest.TestCase):
    def test_fields(self):
        fields=parse_identity('{"brand":"CeraVe","name":"Cleanser","size":"100 ml","shade":null,"approved":true}')
        self.assertEqual(search_name(fields),'CeraVe Cleanser 100 ml')
        self.assertNotIn('approved',fields)
    def test_invalid(self):
        with self.assertRaises(ValueError):
            parse_identity('[]')
    def test_unknown(self):
        self.assertEqual(search_name(parse_identity('{"name":null}')),'')
