from PIL import Image, ImageOps
from .brand_profiles import FORMATS
from pathlib import Path

def render_formats(source,output,formats):
    output=Path(output)
    with Image.open(source) as im:
        if im.width*im.height>25000000: raise ValueError('PIXEL_LIMIT')
        original=ImageOps.exif_transpose(im).convert('RGB')
    result=[]
    for name in dict.fromkeys(formats):
        if name not in FORMATS: raise ValueError('UNKNOWN_FORMAT')
        size=FORMATS[name]
        fitted=ImageOps.contain(original,size,Image.Resampling.LANCZOS)
        canvas=Image.new('RGB',size,'white')
        canvas.paste(fitted,((size[0]-fitted.width)//2,(size[1]-fitted.height)//2))
        path=output/(name+'.png')
        with path.open('xb') as f: canvas.save(f,format='PNG')
        result.append({'file':path.name,'width':size[0],'height':size[1],'resampled':fitted.size!=original.size,'identity_verified':False,'publication_allowed':False})
    return result
