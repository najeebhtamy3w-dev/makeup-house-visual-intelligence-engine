"""Independent scene generation with exact original product pixels."""
from pathlib import Path
import hashlib
from PIL import Image, ImageOps, ImageChops

def compose_scene(source, mask, editor, prompt, output, *, mask_reviewed=False, seed=42, size=1024):
    if not mask_reviewed:
        raise ValueError("HUMAN_MASK_REVIEW_REQUIRED")
    if not isinstance(prompt,str) or not prompt.strip() or len(prompt)>1500:
        raise ValueError("INVALID_PROMPT")
    if size not in (512,768,1024):
        raise ValueError("INVALID_SCENE_SIZE")
    source,mask,output=map(Path,(source,mask,output))
    if output.suffix.lower()!=".png" or output.resolve() in (source.resolve(),mask.resolve()):
        raise ValueError("INVALID_OUTPUT")
    with Image.open(source) as im:
        if im.width*im.height>25000000: raise ValueError("PIXEL_LIMIT")
        original=ImageOps.exif_transpose(im).convert("RGB")
    with Image.open(mask) as im:
        m=im.convert("L")
    if m.size!=original.size or m.getextrema()!=(0,255) or sum(m.histogram()[1:255]):
        raise ValueError("INVALID_BINARY_MASK")
    bounds=m.getbbox()
    if bounds[0]==0 or bounds[1]==0 or bounds[2]==m.width or bounds[3]==m.height:
        raise ValueError("PRODUCT_TOUCHES_FRAME_REVIEW_REQUIRED")
    product=original.crop(bounds)
    alpha=m.crop(bounds)
    # Never rescale protected pixels. Use a larger output canvas when necessary.
    w,h=product.size
    canvas_w=max(size,w*2)
    canvas_h=max(size,(h*3+1)//2)
    if canvas_w*canvas_h>25000000: raise ValueError("CANVAS_LIMIT")
    scene=editor.background("Empty commercial photography set, no products, no bottles, no packaging, no text. "+prompt,width=size,height=size,seed=seed).convert("RGB")
    scene=scene.resize((canvas_w,canvas_h),Image.Resampling.LANCZOS)
    x=(canvas_w-w)//2
    y=(canvas_h-h)*2//3
    scene.paste(product,(x,y),alpha)
    diff=ImageChops.difference(product,scene.crop((x,y,x+w,y+h)))
    if Image.composite(diff,Image.new("RGB",product.size),alpha).getbbox():
        raise RuntimeError("PROTECTED_PIXELS_CHANGED")
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("xb") as f: scene.save(f,format="PNG")
    return {"status":"REVIEW_REQUIRED","protected_pixels_preserved":True,"product_rescaled":False,"mask_reviewed":True,"identity_verified":False,"publication_allowed":False,"placement":[x,y,w,h],"output_sha256":hashlib.sha256(output.read_bytes()).hexdigest()}
