"""Reversible tests: no package installation, network calls or service activation."""
import json
from pathlib import Path
import tempfile
import unittest
from .configuration import read_config
from .prepare import prepare

TOKEN='A1b2C3d4E5f6G7h8I9j0K_l-MnOpQrStUvWx'


def config_text(**overrides):
    values={'MHVIE_DOMAIN':'mhvie.example.com','MHVIE_TOKEN':TOKEN,'MHVIE_SEARX':'https://search.example.com','MHVIE_HOSTS':'cerave.com,example.com','MHVIE_OCR':'0'}
    values.update(overrides)
    return ''.join(key+'='+value+'\n' for key,value in values.items())


class DeploymentTests(unittest.TestCase):
    def test_valid_config_and_model_missing(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'backend.env'
            path.write_text(config_text())
            self.assertEqual(read_config(path)['MHVIE_DOMAIN'],'mhvie.example.com')
            path.write_text(config_text(MHVIE_VISION_MODEL='/unavailable-model-path-for-test'))
            with self.assertRaisesRegex(ValueError,'MODEL_NOT_FOUND_MHVIE_VISION_MODEL'):
                read_config(path)

    def test_placeholder_secret_injection_and_remote_http_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'backend.env'
            for changed in ({'MHVIE_TOKEN':'REPLACE_WITH_SECRET'}, {'MHVIE_TOKEN':'x'*64}, {'MHVIE_SEARX':'http://remote.example.com'}, {'MHVIE_DOMAIN':'domain.example.com;command'}, {'MHVIE_TOKEN':TOKEN+'$(command)'}, {'MHVIE_HOSTS':'example.com,*'}):
                with self.subTest(changed=list(changed)):
                    path.write_text(config_text(**changed))
                    with self.assertRaises(ValueError) as error:
                        read_config(path)
                    self.assertNotIn(TOKEN,str(error.exception))

    def test_prepare_only_renders_nonroot_package_without_deploying(self):
        with tempfile.TemporaryDirectory() as d:
            config=Path(d)/'backend.env'
            config.write_text(config_text())
            prefix=Path(d)/'runtime'
            result=prepare(prefix,config,'mhvie',prepare_only=True)
            self.assertEqual(result['status'],'PREPARED_NOT_INSTALLED')
            self.assertFalse(result['deployed'])
            self.assertFalse((prefix/'venv').exists())
            unit=(prefix/'units/mhvie-worker.service').read_text()
            self.assertIn('User=mhvie',unit)
            self.assertIn('ProtectSystem=strict',unit)
            self.assertNotIn('@PREFIX@',unit)
            self.assertNotIn(TOKEN,unit)
            self.assertIn('reverse_proxy 127.0.0.1:8765',(prefix/'config/Caddyfile').read_text())
            environment=prefix/'config/backend.env'
            self.assertEqual(environment.stat().st_mode & 0o777,0o600)
            self.assertIn('MHVIE_DATA='+str(prefix/'data'),environment.read_text())
            self.assertFalse(json.loads((prefix/'preparation.json').read_text())['models_downloaded'])
            with self.assertRaisesRegex(ValueError,'PREFIX_MUST_BE_EMPTY'):
                prepare(prefix,config,'mhvie',prepare_only=True)

    def test_root_worker_and_unsafe_prefix_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            config=Path(d)/'backend.env'
            config.write_text(config_text())
            with self.assertRaisesRegex(ValueError,'NON_ROOT_SERVICE_USER_REQUIRED'):
                prepare(Path(d)/'runtime',config,'root',prepare_only=True)
            with self.assertRaisesRegex(ValueError,'PREFIX_MUST_BE_SAFE'):
                prepare(Path(d)/'unsafe prefix',config,'mhvie',prepare_only=True)

class SmokeTests(unittest.TestCase):
    def test_authenticated_health_without_secret_or_redirect_leak(self):
        import contextlib
        import io
        import threading
        from http.server import HTTPServer,BaseHTTPRequestHandler
        from unittest.mock import patch
        from .smoke import main
        observed=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*_): pass
            def do_GET(self):
                observed.append(self.headers.get('Authorization'))
                if self.server.redirect:
                    self.send_response(302)
                    self.send_header('Location','https://unrequested.example.com')
                    self.end_headers()
                else:
                    data=b'{"status":"API_AVAILABLE","model_readiness":"NOT_VERIFIED"}'
                    self.send_response(200);self.end_headers();self.wfile.write(data)
        server=HTTPServer(('127.0.0.1',0),Handler)
        server.redirect=False
        thread=threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as d:
                config=Path(d)/'backend.env'
                config.write_text(config_text())
                arguments=['smoke.py','--env',str(config),'--url','http://127.0.0.1:'+str(server.server_port)]
                output=io.StringIO()
                with patch('sys.argv',arguments),contextlib.redirect_stdout(output):
                    self.assertEqual(main(),0)
                self.assertIn('NOT_VERIFIED',output.getvalue())
                self.assertNotIn(TOKEN,output.getvalue())
                self.assertEqual(observed,['Bearer '+TOKEN])
                server.redirect=True
                error=io.StringIO()
                with patch('sys.argv',arguments),contextlib.redirect_stderr(error):
                    self.assertEqual(main(),1)
                self.assertNotIn(TOKEN,error.getvalue())
                self.assertEqual(len(observed),2)
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':
    unittest.main()
