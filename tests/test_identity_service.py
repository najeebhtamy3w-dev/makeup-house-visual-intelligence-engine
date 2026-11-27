import tempfile
import unittest
from pathlib import Path
from PIL import Image
from engine.identity_service import IdentityService

class IdentityServiceTests(unittest.TestCase):
    def test_unverified_result(self):
        class Reader:
            def predict(self,path): return []
        class Model:
            def identify(self,image): return {'fields':{'brand':'QV','name':'Wash'}}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'input.png'
            Image.new('RGB',(64,64)).save(path)
            result=IdentityService(Reader(),Model())(path)
            self.assertEqual(result['fields']['brand'],'QV')
            self.assertFalse(result['identity_verified'])
            self.assertFalse(result['publication_allowed'])
