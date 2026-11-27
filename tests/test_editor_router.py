import unittest
from engine.editor_router import EditorRouter
class RouterTests(unittest.TestCase):
    def test_lazy_and_no_double_load(self):
        calls=[]
        def factory():
            calls.append(1)
            return object()
        router=EditorRouter({'flux':factory,'qwen':factory})
        self.assertEqual(calls,[])
        self.assertIs(router.select(),router.select())
        with self.assertRaisesRegex(RuntimeError,'RESTART'):
            router.select('qwen')
        self.assertEqual(calls,[1])
    def test_unconfigured(self):
        router=EditorRouter({'flux':object})
        with self.assertRaisesRegex(RuntimeError,'NOT_CONFIGURED'):
            router.select('qwen')
