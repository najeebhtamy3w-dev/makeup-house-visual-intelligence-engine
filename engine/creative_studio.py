"""Local generative studio. No automatic publication or remote API."""
from pathlib import Path
import hashlib
from PIL import Image, ImageOps, ImageChops

class LocalEditor:
    def __init__(self,model_dir,backend,device='cuda'):
        import torch
        if backend not in ('qwen','flux'): raise ValueError('UNKNOWN_BACKEND')
        if not Path(model_dir).is_dir(): raise FileNotFoundError('LOCAL_MODEL_REQUIRED')
        if device!='cuda' or not torch.cuda.is_available(): raise RuntimeError('CUDA_REQUIRED_FOR_THIS_PROFILE')
        if backend=='qwen':
            from diffusers import QwenImageEditPlusPipeline
            cls=QwenImageEditPlusPipeline
        else:
            from diffusers import Flux2KleinPipeline
            cls=Flux2KleinPipeline
        native_bf16=torch.cuda.get_device_capability()[0]>=8
        if backend=='qwen' and not native_bf16: raise RuntimeError('NATIVE_BF16_REQUIRED_FOR_QWEN_PROFILE')
        dtype=torch.bfloat16 if native_bf16 else torch.float16
        self.pipeline=cls.from_pretrained(model_dir,torch_dtype=dtype,local_files_only=True)
        self.pipeline.enable_model_cpu_offload()
        self.pipeline.vae.enable_slicing()
        self.pipeline.vae.enable_tiling()
        self.backend=backend
    def background(self,prompt,width=768,height=768,seed=42):
        import torch
        if self.backend!='flux': raise ValueError('FLUX_BACKGROUND_REQUIRED')
        if not (256<=width<=1024 and 256<=height<=1024 and width%16==0 and height%16==0): raise ValueError('INVALID_DIMENSIONS')
        return self.pipeline(prompt=prompt,width=width,height=height,num_inference_steps=4,guidance_scale=1.0,generator=torch.Generator(device='cpu').manual_seed(seed)).images[0]
    def edit(self,image,prompt,seed=42):
        import torch
        # Bound generation cost independently of original product resolution.
        image=image.copy()
        image.thumbnail((1024,1024),Image.Resampling.LANCZOS)
        kwargs={'image':image,'prompt':prompt,'generator':torch.Generator(device='cpu').manual_seed(seed)}
        if self.backend=='qwen':
            kwargs.update(num_inference_steps=40,true_cfg_scale=4.0)
        else:
            kwargs.update(num_inference_steps=4,guidance_scale=1.0)
        return self.pipeline(**kwargs).images[0]

def protected_edit(source,mask,prompt,editor,output,seed=42):
    """Mask white protects original pixels; black permits generated background."""
    if not isinstance(prompt,str) or not prompt.strip() or len(prompt)>2000:
        raise ValueError('INVALID_PROMPT')
    source,mask,output=map(Path,(source,mask,output))
    if output.resolve() in (source.resolve(),mask.resolve()):
        raise ValueError('ORIGINAL_OVERWRITE')
    with Image.open(source) as im:
        if im.width*im.height>25000000: raise ValueError('PIXEL_LIMIT')
        original=ImageOps.exif_transpose(im).convert('RGB')
    with Image.open(mask) as im:
        if im.size!=original.size: raise ValueError('MASK_SIZE_MISMATCH')
        protected=im.convert('L').point(lambda x:255 if x>0 else 0)
    if protected.getextrema()!=(0,255): raise ValueError('INVALID_PROTECTION_MASK')
    generated=editor.edit(original.copy(),prompt,seed).convert('RGB')
    if generated.size!=original.size:
        generated=generated.resize(original.size,Image.Resampling.LANCZOS)
    result=Image.composite(original,generated,protected)
    diff=ImageChops.difference(original,result)
    if Image.composite(diff,Image.new('RGB',original.size),protected).getbbox():
        raise RuntimeError('PROTECTED_PIXELS_CHANGED')
    if output.suffix.lower()!='.png': raise ValueError('LOSSLESS_PNG_REQUIRED')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as stream: result.save(stream,format='PNG')
    return {'status':'REVIEW_REQUIRED','protected_pixels_preserved':True,'mask_verified':False,'identity_verified':False,'publication_allowed':False,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'seed':seed}


class LazyEditor:
    """Single-worker lazy initialization; failed loads are not cached."""
    def __init__(self,factory):
        self.factory=factory
        self.editor=None
    def edit(self,image,prompt,seed=42):
        if self.editor is None:
            self.editor=self.factory()
        return self.editor.edit(image,prompt,seed)
