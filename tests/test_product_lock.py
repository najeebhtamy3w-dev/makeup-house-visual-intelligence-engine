import tempfile
import unittest
from pathlib import Path
from PIL import Image
from engine.product_lock import prepare_mask,verify_pixels

class FixtureSegmenter:
    def segment(self,image):
        m=Image.new('L',image.size)
        m.paste(255,(20,20,44,44))
        return m

class LockTests(unittest.TestCase):
    def test_mask_and_verification(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            a=p/'a.png'; b=p/'b.png'; m=p/'mask.png'
            Image.new('RGB',(64,64),'red').save(a)
            report=prepare_mask(a,m,FixtureSegmenter())
            self.assertFalse(report['mask_verified'])
            im=Image.new('RGB',(64,64),'red')
            im.putpixel((0,0),(0,0,255)); im.save(b)
            self.assertTrue(verify_pixels(a,b,m)['protected_pixels_preserved'])
            im.putpixel((30,30),(0,0,255)); im.save(b)
            self.assertEqual(verify_pixels(a,b,m)['changed_protected_pixels'],1)
    def test_empty_mask(self):
        class Empty:
            def segment(self,image): return Image.new('L',image.size)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); Image.new('RGB',(64,64)).save(p/'a.png')
            with self.assertRaises(ValueError): prepare_mask(p/'a.png',p/'m.png',Empty())
