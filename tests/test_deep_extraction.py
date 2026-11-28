import unittest
from engine.deep_extraction import extract

class ExtractionTests(unittest.TestCase):
    def test_product_gallery_and_dedup(self):
        html = '''<meta property="og:image" content="/logo.png">
        <img src="http://example.com/a.jpg" srcset="/a.jpg 1200w, /b.jpg 800w">
        <script type="application/ld+json">{"@type":"Product","image":["/a.jpg","/c.jpg"]}</script>'''
        rows = extract("https://example.com/product", html)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["url"], "https://example.com/a.jpg")
        self.assertEqual(rows[0]["declared_width"], 1200)
        self.assertEqual(rows[0]["rights"], "RIGHTS_UNVERIFIED")
        self.assertEqual(rows[0]["status"], "NEEDS_MANUAL_REVIEW")

    def test_invalid_urls(self):
        self.assertEqual(extract("https://example.com", '<img src="data:image/png;base64,x"><img src="https://user:pass@example.com/a"><img src="https://example.com:8080/a">'), [])

    def test_limit_after_dedup(self):
        self.assertEqual(len(extract("https://example.com", '<img src="/a"><img src="/a"><img src="/b">', 2)), 2)

    def test_nested_product(self):
        rows = extract("https://example.com", '<script type="application/ld+json">{"@graph":[{"@type":["Product"],"image":{"contentUrl":"/a.png"}}]}</script>')
        self.assertEqual(rows[0]["methods"], ["product_jsonld"])

if __name__ == "__main__":
    unittest.main()
