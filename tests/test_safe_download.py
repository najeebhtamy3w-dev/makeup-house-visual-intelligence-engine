import io
import unittest
from unittest.mock import patch
from PIL import Image
from engine.safe_download import validate_url, public_address, inspect_image

class DownloadTests(unittest.TestCase):
    def test_url_policy(self):
        for url in ['http://example.com/a','https://example.com.evil.org/a','https://user@example.com/a','https://example.com:8080/a']:
            with self.assertRaises(ValueError):
                validate_url(url,['example.com'])
        self.assertEqual(validate_url('https://cdn.example.com/a',['example.com']).hostname,'cdn.example.com')

    def test_private_dns(self):
        with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaises(ValueError):
                public_address('example.com')

    def test_image(self):
        buf=io.BytesIO()
        Image.new('RGB',(100,100)).save(buf,format='PNG')
        data=buf.getvalue()
        self.assertEqual(inspect_image(data,'image/png')['width'],100)
        with self.assertRaises(ValueError):
            inspect_image(data,'image/jpeg')

    def test_corrupt_image(self):
        with self.assertRaises(OSError):
            inspect_image(b'not an image','image/png')
