import unittest
from engine.creative_studio import LazyEditor

class LazyEditorTests(unittest.TestCase):
    def test_reuse(self):
        loads=[]
        class Editor:
            def edit(self,image,prompt,seed): return (image,prompt,seed)
        def factory():
            loads.append(1)
            return Editor()
        editor=LazyEditor(factory)
        self.assertEqual(loads,[])
        self.assertEqual(editor.edit('a','b'),('a','b',42))
        editor.edit('c','d')
        self.assertEqual(loads,[1])
    def test_failed_load_can_retry(self):
        calls=[]
        def factory():
            calls.append(1)
            raise RuntimeError('unavailable')
        editor=LazyEditor(factory)
        for _ in range(2):
            with self.assertRaises(RuntimeError): editor.edit(None,'test')
        self.assertEqual(len(calls),2)
