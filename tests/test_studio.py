import io, hashlib, unittest
from PIL import Image
from engine.studio import render
from engine.rights import decision, permitted

class StudioTests(unittest.TestCase):
    def test_preview_and_rights(self):
        b=io.BytesIO()
        Image.new('RGB',(200,300),'red').save(b,format='PNG')
        data=b.getvalue()
        digest=hashlib.sha256(data).hexdigest()
        source='https://example.org/product'
        record=decision(digest,source,'reviewer','permission reference',commercial=True,derivatives=True,sku_confirmed=True)
        out,meta=render(data,source,(400,400),record=record)
        self.assertTrue(meta['rights_eligible'])
        self.assertFalse(meta['commercial_approved'])
        self.assertEqual(Image.open(io.BytesIO(out)).size,(400,400))
        self.assertFalse(permitted(record,digest,'other',derivative=True))
        self.assertFalse(render(data,source)[1]['rights_eligible'])
        with self.assertRaises(ValueError):
            render(data,source,mask=Image.new('L',(1,1)))
    def test_derivative_denied(self):
        digest='a'*64
        r=decision(digest,'source','reviewer','evidence',commercial=True,sku_confirmed=True)
        self.assertFalse(permitted(r,digest,'source',derivative=True))
