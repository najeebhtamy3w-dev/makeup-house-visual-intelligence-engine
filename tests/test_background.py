import io, unittest
from PIL import Image, ImageDraw
from engine.background import preview, validate_mask

class Fake:
    def mask(self,im):
        m=Image.new('L',im.size)
        ImageDraw.Draw(m).rectangle((20,20,80,80),fill=255)
        return m

class BackgroundTests(unittest.TestCase):
    def test_preview(self):
        b=io.BytesIO()
        Image.new('RGB',(100,100),'red').save(b,format='PNG')
        out,meta=preview(b.getvalue(),'test',Fake(),size=(256,256))
        self.assertTrue(meta['mask_applied'])
        self.assertFalse(meta['commercial_approved'])
        self.assertEqual(Image.open(io.BytesIO(out)).size,(256,256))
    def test_degenerate(self):
        for color in (0,255):
            with self.assertRaises(ValueError):
                validate_mask(Image.new('L',(100,100),color),(100,100))
