import unittest
from engine.multi_input import resolve_input

class InputConflicts(unittest.TestCase):
    def test_conflict(self):
        def forbidden(*args): self.fail('unexpected search')
        r=resolve_input('4006381333931',None,'photo',forbidden,forbidden,forbidden,lambda p:[{'text':'5901234123457'}])
        self.assertEqual(r['route'],'BARCODE_PHOTO_CONFLICT')
        self.assertFalse(r['publication_allowed'])
    def test_rejected_and_empty(self):
        code='4006381333931'
        evidence=[{'fields':{'gtin':code,'brand':'QV','name':'Cleanser','size':'250g'}}]
        for rows in ([],[{'selection':{'status':'REJECTED'}}]):
            r=resolve_input(code,None,'photo',lambda c:evidence,lambda p:{'candidates':[]},lambda q:{'candidates':rows},lambda p:[])
            self.assertEqual(r['route'],'PHOTO_FALLBACK')
            self.assertIn('BARCODE_NO_USABLE_IMAGES',r['route_trace'])
    def test_invalid_before_scan(self):
        def forbidden(*args): self.fail('unexpected scan')
        with self.assertRaises(ValueError):
            resolve_input('123',None,'photo',forbidden,forbidden,forbidden,forbidden)
