import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from engine.locked_scene import compose_scene

class Editor:
    def background(self,prompt,width,height,seed):
        return Image.new("RGB",(width,height),"gold")

class LockedSceneTests(unittest.TestCase):
    def test_preservation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            a=Image.new("RGB",(100,100),"white")
            ImageDraw.Draw(a).rectangle((20,20,79,79),fill="blue")
            a.save(p/"source.png")
            m=Image.new("L",a.size)
            ImageDraw.Draw(m).rectangle((20,20,79,79),fill=255)
            m.save(p/"mask.png")
            with self.assertRaisesRegex(ValueError,"HUMAN_MASK"):
                compose_scene(p/"source.png",p/"mask.png",Editor(),"marble",p/"out.png")
            report=compose_scene(p/"source.png",p/"mask.png",Editor(),"marble",p/"out.png",mask_reviewed=True,size=512)
            x,y,w,h=report["placement"]
            with Image.open(p/"out.png") as out:
                self.assertEqual(out.crop((x,y,x+w,y+h)).tobytes(),a.crop((20,20,80,80)).tobytes())
            self.assertFalse(report["publication_allowed"])
            self.assertFalse(report["identity_verified"])
