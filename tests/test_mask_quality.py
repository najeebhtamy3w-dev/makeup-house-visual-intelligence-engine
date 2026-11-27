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
