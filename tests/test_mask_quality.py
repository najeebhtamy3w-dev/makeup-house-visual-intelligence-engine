import unittest
from PIL import Image
from engine.mask_quality import refine_mask

class MaskQualityTests(unittest.TestCase):
    def test_noise_and_uncertain_edge(self):
        p=Image.new("L",(100,100))
        p.paste(255,(20,20,70,80))
        p.putpixel((95,95),255)
        p.putpixel((19,30),80)
        m,q=refine_mask(p)
        self.assertEqual(m.getpixel((95,95)),0)
        self.assertEqual(m.getpixel((19,30)),0)
        self.assertEqual(m.getpixel((20,30)),255)
        self.assertTrue(q["human_review_required"])
    def test_multiple_objects(self):
        p=Image.new("L",(100,100))
        p.paste(255,(0,10,40,80))
        p.paste(255,(60,30,90,60))
        m,q=refine_mask(p)
        self.assertIn("MULTIPLE_OBJECTS",q["flags"])
        self.assertIn("TOUCHES_FRAME",q["flags"])
        self.assertEqual(m.getpixel((70,40)),255)
    def test_optional_detail_protection_preserves_thin_connected_stem(self):
        from PIL import ImageDraw
        p=Image.new('L',(1536,1536))
        draw=ImageDraw.Draw(p)
        draw.rectangle((500,500,1000,1300),fill=255)
        draw.line((750,500,750,100),fill=255,width=1)
        legacy,legacy_quality=refine_mask(p)
        protected,quality=refine_mask(p,preserve_details=True)
        self.assertEqual(legacy.getpixel((750,200)),0)
        self.assertEqual(protected.getpixel((750,200)),255)
        self.assertEqual(protected.tobytes(),p.tobytes())
        self.assertEqual(quality['cleanup_removed_foreground_pixels'],399)
        self.assertEqual(quality['removed_foreground_pixels'],0)
        self.assertTrue(quality['detail_protection_applied'])
        self.assertIn('DETAIL_LOSS_REVIEW_REQUIRED',quality['flags'])
        self.assertEqual(legacy_quality['removed_foreground_pixels'],399)

    def test_optional_protection_still_cleans_single_isolated_speck(self):
        p=Image.new('L',(100,100)); p.paste(255,(20,20,70,80)); p.putpixel((95,95),255)
        m,q=refine_mask(p,preserve_details=True)
        self.assertEqual(m.getpixel((95,95)),0)
        self.assertFalse(q['detail_protection_applied'])
        self.assertEqual(q['removed_foreground_pixels'],1)
