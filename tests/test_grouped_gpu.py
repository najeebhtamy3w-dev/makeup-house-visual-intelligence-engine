import hashlib,io,json,tempfile,unittest
from pathlib import Path
from PIL import Image
from engine.studio_benchmark import dataset,run_group

class GroupedGPUTests(unittest.TestCase):
    def photos(self,root):
        rows=[]
        for i in range(10):
            p=root/f'{i}.png';Image.new('RGB',(40,40),(i,20,30)).save(p)
            rows.append({'image':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        manifest=root/'manifest.json';manifest.write_text(json.dumps(rows))
        return manifest

    def test_one_load_ten_edits_and_originals_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);manifest=self.photos(root);calls=[]
            class Editor:
                def __init__(self,*args):calls.append('load')
                def edit(self,image,prompt,seed):calls.append((prompt,seed));return image.copy()
            rows=run_group(root,manifest,root,'flux',root/'out','same prompt',editor_factory=Editor)
            self.assertEqual(calls.count('load'),1)
            self.assertEqual(calls[1:],[('same prompt',42)]*10)
            self.assertEqual(len(rows),10)
            self.assertTrue(all(r['status']=='REVIEW_REQUIRED' and not r['publication_allowed'] and not r['real_inference_verified'] for r in rows))
            self.assertEqual(len(dataset(root,manifest)),10)

    def test_missing_weights_yields_ten_blocked_not_fake_inference(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);manifest=self.photos(root)
            rows=run_group(root,manifest,root/'missing','flux',root/'out','prompt')
            self.assertEqual(len(rows),10)
            self.assertTrue(all(r['status']=='BLOCKED' for r in rows))
            self.assertEqual(json.loads((root/'out/group.json').read_text())['model_load_count'],0)

    def test_tampered_dataset_is_rejected_before_model_load(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);manifest=self.photos(root);(root/'0.png').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'DATASET_HASH_MISMATCH'):dataset(root,manifest)
