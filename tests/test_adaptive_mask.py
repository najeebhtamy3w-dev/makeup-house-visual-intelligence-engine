import unittest,tempfile
from pathlib import Path
from PIL import Image
from engine.adaptive_mask import adaptive_mask
from engine.mask_review import correct_mask

class Segmenter:
    def __init__(self): self.calls=0
    def segment(self,image):
        self.calls+=1
        m=Image.new("L",image.size)
        m.paste(255,(0,10,40,80))
        return m

class AdaptiveTests(unittest.TestCase):
    def test_unstable(self):
        s=Segmenter()
        m,r=adaptive_mask(Image.new("RGB",(100,100)),s)
        self.assertEqual(s.calls,2)
        self.assertIn("UNSTABLE_SEGMENTATION",r["quality"]["flags"])
        self.assertFalse(r["mask_verified"])
    def test_correction(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            Image.new("RGB",(100,100),"red").save(p/"source.png")
            m=Image.new("L",(100,100))
            m.paste(255,(10,10,90,90))
            m.save(p/"mask.png")
            r=correct_mask(p/"source.png",p/"mask.png",p/"out.png",[{"mode":"erase","radius":5,"points":[[20,20]]}])
            with Image.open(p/"out.png") as out:
                self.assertEqual(out.getpixel((20,20)),0)
                self.assertEqual(out.getpixel((50,50)),255)
            self.assertFalse(r["mask_verified"])
            self.assertTrue((p/"preview.png").exists())
