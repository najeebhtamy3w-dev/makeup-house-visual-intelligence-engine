import unittest
from engine.visual_evaluator import PROMPTS,CLASSIFICATION_VERSION

class VisualPromptContract(unittest.TestCase):
    def test_balanced_taxonomy(self):
        self.assertEqual(len(PROMPTS),9)
        self.assertTrue(all(len(v)==3 for v in PROMPTS.values()))
        self.assertEqual(len({p for v in PROMPTS.values() for p in v}),27)
    def test_packaging_distinction(self):
        self.assertTrue(all('without' in p or 'only' in p for p in PROMPTS['texture']))
        self.assertEqual(CLASSIFICATION_VERSION,'prompt-ensemble-v2')
