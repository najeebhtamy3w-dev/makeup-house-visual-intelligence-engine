import tempfile
import unittest
from pathlib import Path
from PIL import Image
from engine.candidate_quality import assess, distance

class CandidateQualityTests(unittest.TestCase):
    def test_quality_never_approves_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'test.png'
            Image.new('RGB',(700,700),'white').save(p)
            result=assess(p)
            self.assertTrue(result['resolution_ok'])
            self.assertFalse(result['identity_verified'])
            self.assertEqual(result['rights'],'RIGHTS_UNVERIFIED')
            self.assertEqual(distance(result['dhash'],result['dhash']),0)
    def test_distance(self):
        self.assertEqual(distance('0000000000000000','ffffffffffffffff'),64)
