import unittest
from unittest.mock import patch
from engine.instagram_finder import find

class InstagramFinderTests(unittest.TestCase):
    @patch("engine.instagram_finder.discover")
    def test_exclusive(self,discover):
        calls=[]
        def search(q):
            calls.append(q)
            return [{"url":"https://instagram.com/p/abc/"},{"url":"https://example.com/product"},{"url":"https://instagram.com/profile/"}]
        discover.return_value={"candidates":[],"errors":[]}
        result=find("Mielle",search,"unused")
        self.assertEqual(calls,["Mielle site:instagram.com"])
        self.assertEqual(discover.call_args.args[1](""),[{"url":"https://instagram.com/p/abc/"}])
        self.assertEqual(result["status"],"NO_CANDIDATES")
    @patch("engine.instagram_finder.discover")
    def test_reject_external_source(self,discover):
        discover.return_value={"candidates":[{"source":"https://example.com/product","url":"https://example.com/a.jpg","sha256":"x","width":1000,"height":1000}],"errors":[]}
        self.assertFalse(find("Mielle",lambda q:[],"unused")["candidates"])
