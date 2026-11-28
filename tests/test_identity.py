import unittest
from engine.identity import valid_gtin, assess, sizes

class IdentityTests(unittest.TestCase):
    def test_gtin(self):
        self.assertTrue(valid_gtin('4006381333931'))
        self.assertFalse(valid_gtin('4006381333932'))
        self.assertFalse(valid_gtin(None))
    def test_size_conflict(self):
        row=assess({'size':'100 ml'},{'size':'200 ml'},0.99)
        self.assertEqual(row['status'],'SKU_CONFLICT')
    def test_equivalent_size(self):
        self.assertEqual(sizes('1 L'),sizes('1000 ml'))
    def test_barcode_match(self):
        row=assess({'barcode':'4006381333931'},{'barcode':'04006381333931'})
        self.assertEqual(row['status'],'BARCODE_MATCH_REVIEW_REQUIRED')
        self.assertFalse(row['commercial_approved'])
    def test_visual_only(self):
        self.assertEqual(assess({}, {}, 0.99)['status'],'INSUFFICIENT_SKU_EVIDENCE')
