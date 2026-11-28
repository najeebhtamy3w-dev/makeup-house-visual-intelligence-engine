import unittest
from PIL import Image
from engine.visual_quality import signals, distance, near_duplicate

class QualityTests(unittest.TestCase):
    def test_resolution(self):
        row=signals(Image.new('RGB',(100,100)))
        self.assertEqual(row['resolution_status'],'LOW_RESOLUTION')
        self.assertEqual(row['sku_status'],'UNVERIFIED')

    def test_hash(self):
        self.assertEqual(distance('0000000000000000','000000000000000f'),4)
        self.assertTrue(near_duplicate('0','f'))
        self.assertFalse(near_duplicate('0','ff'))

    def test_identical_resize(self):
        im=Image.new('RGB',(100,100),'white')
        self.assertEqual(signals(im)['dhash'],signals(im.resize((500,500)))['dhash'])
