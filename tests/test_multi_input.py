import unittest
from engine.multi_input import resolve_input

class MultiInputTests(unittest.TestCase):
    def test_routes(self):
        code='4006381333931'
        item={'fields':{'gtin':code,'brand':'QV','name':'Cleanser','size':'250g'}}
        def named(q): return {'query':q}
        def visual(p): return {'photo':p}
        r=resolve_input(code,None,'photo',lambda c:[item],lambda p:self.fail('visual called'),named)
        self.assertEqual(r['route'],'BARCODE_CATALOG')
        self.assertFalse(r['identity_verified'])
        self.assertEqual(r['input_consistency'],'REVIEW_REQUIRED')
        for evidence in ([],[item,{'fields':dict(item['fields'],size='500g')}]):
            self.assertEqual(resolve_input(code,None,'photo',lambda c:evidence,visual,named)['route'],'PHOTO_FALLBACK')
        self.assertEqual(resolve_input(code,'QV',None,lambda c:[],visual,named)['route'],'NAME_FALLBACK')
        self.assertEqual(resolve_input(code,None,None,lambda c:[],visual,named)['status'],'ADDITIONAL_INPUT_REQUIRED')
        with self.assertRaises(ValueError): resolve_input('123',None,None,lambda c:[],visual,named)
