import tempfile
import unittest
from pathlib import Path
from PIL import Image
from engine.creative_studio import protected_edit

class FixtureEditor:
    def edit(self,image,prompt,seed):
        return Image.new('RGB',image.size,'blue')

class StudioTests(unittest.TestCase):
    def test_protected_composite(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=root/'original.png'; mask=root/'mask.png'; out=root/'edited.png'
            Image.new('RGB',(64,64),'red').save(source)
            m=Image.new('L',(64,64),0)
            m.paste(255,(16,16,48,48)); m.save(mask)
            before=source.read_bytes()
            report=protected_edit(source,mask,'blue background',FixtureEditor(),out)
            with Image.open(out) as im:
                self.assertEqual(im.getpixel((32,32)),(255,0,0))
                self.assertEqual(im.getpixel((0,0)),(0,0,255))
            self.assertEqual(source.read_bytes(),before)
            self.assertFalse(report['publication_allowed'])
            self.assertFalse(report['identity_verified'])
            with self.assertRaises(ValueError):
                protected_edit(source,mask,'test',FixtureEditor(),source)
    def test_empty_mask(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            Image.new('RGB',(32,32)).save(root/'source.png')
            Image.new('L',(32,32)).save(root/'mask.png')
            with self.assertRaises(ValueError):
                protected_edit(root/'source.png',root/'mask.png','test',FixtureEditor(),root/'out.png')
