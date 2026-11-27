import unittest
from unittest.mock import patch
from engine.priority_discovery import priority_discover
class PriorityTests(unittest.TestCase):
    @patch("engine.priority_discovery.discover")
    def test_order(self,discover):
        discover.return_value={"status":"NO_CANDIDATES","candidates":[],"errors":[]}
        calls=[]
        def search(q):
            calls.append(q)
            return []
        result=priority_discover("QV cleanser",search,(),"/tmp/unused")
        self.assertIn("site:instagram.com",calls[0])
        self.assertEqual(calls[1],"QV cleanser")
        self.assertTrue(result["creative_fallback_requires_user_choice"])
        self.assertFalse(result["publication_allowed"])
