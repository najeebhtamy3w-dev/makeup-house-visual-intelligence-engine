import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from PIL import Image
from engine.instagram_export import export_selected

class ExportTests(unittest.TestCase):
    def test_selected_export(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"0").mkdir()
            buf=io.BytesIO()
            Image.new("RGB",(600,600)).save(buf,"PNG")
            data=buf.getvalue()
            digest=hashlib.sha256(data).hexdigest()
            path=root/"0"/(digest+".bin")
            path.write_bytes(data)
            report=[{"query":"Product","candidates":[{"sha256":digest,"source":"https://www.instagram.com/p/example/"}]}]
            dest=root/"selected.zip"
            manifest=export_selected(root,report,[(0,digest),(0,digest)],dest)
            self.assertEqual(len(manifest),1)
            with ZipFile(dest) as z:
                self.assertEqual(z.read(manifest[0]["file"]),data)
                self.assertIn("manifest.json",z.namelist())
            path.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError,"HASH_MISMATCH"):
                export_selected(root,report,[(0,digest)],dest)
            with self.assertRaisesRegex(ValueError,"INVALID_SELECTION"):
                export_selected(root,report,[(0,"../bad")],dest)
