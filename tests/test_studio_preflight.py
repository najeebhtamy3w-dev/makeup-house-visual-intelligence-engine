import unittest
from unittest.mock import patch
import types
from engine.studio_preflight import assess

class StudioPreflightTests(unittest.TestCase):
    def test_t4_flux_fp16_ready_but_qwen_blocked(self):
        cuda=types.SimpleNamespace(is_available=lambda:True,
            get_device_properties=lambda _:types.SimpleNamespace(name='Synthetic T4 profile',total_memory=16*1024**3),
            get_device_capability=lambda:(7,5),is_bf16_supported=lambda:False)
        torch=types.SimpleNamespace(__version__='fixture',cuda=cuda)
        diffusers=types.SimpleNamespace(__version__='fixture',Flux2KleinPipeline=object,QwenImageEditPlusPipeline=object)
        with patch.dict('sys.modules',{'torch':torch,'diffusers':diffusers}), patch('engine.studio_preflight.Path.is_file',return_value=True):
            flux=assess('flux','/local/fixture'); qwen=assess('qwen','/local/fixture')
        self.assertTrue(flux['ready'])
        self.assertEqual(flux['selected_dtype'],'float16')
        self.assertFalse(qwen['ready'])
        self.assertEqual(qwen['blockers'],['NATIVE_BF16_REQUIRED_FOR_QWEN_PROFILE'])
        self.assertFalse(flux['inference_verified'])

    def test_missing_cuda_remains_blocked(self):
        torch=types.SimpleNamespace(__version__='fixture',cuda=types.SimpleNamespace(is_available=lambda:False))
        diffusers=types.SimpleNamespace(__version__='fixture',Flux2KleinPipeline=object)
        with patch.dict('sys.modules',{'torch':torch,'diffusers':diffusers}), patch('engine.studio_preflight.Path.is_file',return_value=True):
            result=assess('flux','/local/fixture')
        self.assertFalse(result['ready']); self.assertIn('GPU_UNAVAILABLE',result['blockers'])

    def test_missing_index_and_pipeline_are_explicit(self):
        cuda=types.SimpleNamespace(is_available=lambda:True,
            get_device_properties=lambda _:types.SimpleNamespace(name='Synthetic Ampere profile',total_memory=24*1024**3),
            get_device_capability=lambda:(8,0),is_bf16_supported=lambda:True)
        torch=types.SimpleNamespace(__version__='fixture',cuda=cuda)
        with patch.dict('sys.modules',{'torch':torch,'diffusers':types.SimpleNamespace(__version__='fixture')}), patch('engine.studio_preflight.Path.is_file',return_value=False):
            result=assess('qwen','/local/fixture')
        self.assertFalse(result['ready'])
        self.assertEqual(result['blockers'],['PIPELINE_UNAVAILABLE','LOCAL_MODEL_INDEX_REQUIRED'])
        self.assertEqual(result['selected_dtype'],'bfloat16')
