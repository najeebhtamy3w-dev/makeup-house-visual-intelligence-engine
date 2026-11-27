import unittest
from engine.multimodal import parse_identity, search_name, visual_budget

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

    def test_textual_unknown(self):
        self.assertEqual(parse_identity('{"brand":"null","name":" unknown ","size":"30 ml"}'),{'size':'30 ml'})

    def test_model_specific_budget(self):
        self.assertEqual(visual_budget('qwen3_vl',384)['longest_edge'],384*32**2)
        self.assertEqual(visual_budget('qwen2_5_vl',384)['longest_edge'],384*28**2)
        with self.assertRaises(ValueError): visual_budget('qwen3_vl',0)
