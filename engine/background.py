"""Optional BiRefNet segmentation; never grants commercial approval."""
import io
from PIL import Image, ImageOps
from .studio import render

class BackgroundRemover:
    def __init__(self, session=None):
        if session is None:
            from rembg import new_session
            session=new_session('birefnet-general',providers=['CPUExecutionProvider'])
        self.session=session

    def mask(self, image):
        from rembg import remove
        mask=remove(image.convert('RGB'),session=self.session,only_mask=True,post_process_mask=False)
        return validate_mask(mask,image.size)

def validate_mask(mask,size):
    if not isinstance(mask,Image.Image) or mask.mode!='L' or mask.size!=size:
        raise ValueError('INVALID_SEGMENTATION_MASK')
    fraction=sum(mask.histogram()[128:])/(size[0]*size[1])
    if not .01<fraction<.99:
        raise ValueError('DEGENERATE_SEGMENTATION_MASK')
    return mask

def preview(data,source,remover,**options):
    with Image.open(io.BytesIO(data)) as raw:
        if raw.width*raw.height>25000000:
            raise ValueError('PIXEL_LIMIT')
        im=ImageOps.exif_transpose(raw).convert('RGB')
    mask=validate_mask(remover.mask(im),im.size)
    output,meta=render(data,source,mask=mask,**options)
    meta.update(segmentation_status='REVIEW_REQUIRED',commercial_approved=False)
    return output,meta
