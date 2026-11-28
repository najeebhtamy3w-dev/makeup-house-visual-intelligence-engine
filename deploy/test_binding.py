"""Cloud binding must preserve local deployment defaults and reject bad ports."""
import unittest
from engine.service_main import api_binding

class BindingTests(unittest.TestCase):
    def test_local_default(self):
        self.assertEqual(api_binding({}), ('127.0.0.1', 8765))

    def test_cloud_opt_in(self):
        self.assertEqual(api_binding({'MHVIE_API_HOST':'0.0.0.0','MHVIE_API_PORT':'10000'}), ('0.0.0.0', 10000))
        self.assertEqual(api_binding({'MHVIE_API_HOST':'::','MHVIE_API_PORT':'443'}), ('::', 443))

    def test_bad_bindings(self):
        for changes in ({'MHVIE_API_PORT':'0'}, {'MHVIE_API_PORT':'65536'}, {'MHVIE_API_PORT':'bad'}, {'MHVIE_API_HOST':'https://example.com'}):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError, 'INVALID_API_BINDING'):
                    api_binding(changes)
