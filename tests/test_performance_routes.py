import unittest
from engine.barcode_priority import valid_gtins,matching_evidence
from engine.lazy_vision import LazyVision

class PerformanceRoutes(unittest.TestCase):
    def test_gtin(self):
        codes=[{'text':'4006381333931'},{'text':'4006381333932'},{'text':'https://example.com'}]
        self.assertEqual(valid_gtins(codes),['04006381333931'])
        good={'fields':{'gtin':'4006381333931'}}
        self.assertEqual(matching_evidence([good,{'fields':{'gtin':'4006381333932'}}],'04006381333931'),[good])
    def test_lazy(self):
        calls=[]
        class Model:
            def identify(self,image): return {'fields':{'name':'fixture'}}
        def factory():
            calls.append(1)
            return Model()
        model=LazyVision(factory)
        self.assertEqual(calls,[])
        self.assertTrue(model.identify(None)['vision_runtime']['cold_start'])
        self.assertFalse(model.identify(None)['vision_runtime']['cold_start'])
        self.assertEqual(calls,[1])
