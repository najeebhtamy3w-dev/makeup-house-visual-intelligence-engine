"""Non-generative, non-destructive product layout previews."""
import hashlib, io
from PIL import Image, ImageOps
from .rights import permitted

def render(data, source, size=(1080,1080), background='#ffffff', mask=None, record=None):
    digest=hashlib.sha256(data).hexdigest()
    if len(size)!=2 or any(type(x) is not int or not 128<=x<=2048 for x in size):
        raise ValueError('INVALID_CANVAS')
    with Image.open(io.BytesIO(data)) as raw:
        if raw.width*raw.height>25000000:
            raise ValueError('PIXEL_LIMIT')
        im=ImageOps.exif_transpose(raw).convert('RGBA')
    if mask is not None:
        if mask.size!=im.size or mask.mode!='L':
            raise ValueError('INVALID_MASK')
        from PIL import ImageChops
        im.putalpha(ImageChops.multiply(im.getchannel('A'),mask))
    im.thumbnail(tuple(int(x*.86) for x in size),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',size,background)
    canvas.alpha_composite(im,((size[0]-im.width)//2,(size[1]-im.height)//2))
    out=io.BytesIO()
    canvas.convert('RGB').save(out,format='PNG')
    result=out.getvalue()
    return result,dict(source_sha256=digest,source=source,output_sha256=hashlib.sha256(result).hexdigest(),size=list(size),mask_applied=mask is not None,commercial_approved=False,rights_eligible=permitted(record,digest,source,derivative=True),status='DERIVATIVE_REVIEW_REQUIRED')
