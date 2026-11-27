"""Product mask generation and lossless protected-region verification."""
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter, ImageChops
import hashlib

class BackgroundSegmenter:
    def __init__(self,model='birefnet-general'):
        from rembg import new_session
        self.session=new_session(model,providers=['CPUExecutionProvider'])
    def segment(self,image):
        from rembg import remove
        return remove(image,session=self.session,only_mask=True).convert('L')

def prepare_mask(source,output,segmenter,threshold=32,padding=5):
    if not 1<=threshold<=254 or not 0<=padding<=15:
        raise ValueError('INVALID_MASK_PARAMETERS')
    source,output=Path(source),Path(output)
    if source.resolve()==output.resolve(): raise ValueError('ORIGINAL_OVERWRITE')
    with Image.open(source) as im:
        if im.width*im.height>25000000: raise ValueError('PIXEL_LIMIT')
        image=ImageOps.exif_transpose(im).convert('RGB')
    mask=segmenter.segment(image)
    if mask.size!=image.size: raise ValueError('MASK_SIZE_MISMATCH')
    mask=mask.convert('L').point(lambda x:255 if x>=threshold else 0)
    if padding: mask=mask.filter(ImageFilter.MaxFilter(2*padding+1))
    coverage=mask.histogram()[255]/(mask.width*mask.height)
    if not .01<=coverage<=.95: raise ValueError('MASK_COVERAGE_REVIEW_REQUIRED')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as f: mask.save(f,format='PNG')
    return {'coverage':coverage,'status':'MASK_REVIEW_REQUIRED','mask_verified':False,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}

def verify_pixels(source,edited,mask):
    with Image.open(source) as im: a=ImageOps.exif_transpose(im).convert('RGB')
    with Image.open(edited) as im: b=im.convert('RGB')
    with Image.open(mask) as im: m=im.convert('L')
    if a.size!=b.size or a.size!=m.size: raise ValueError('SIZE_MISMATCH')
    if m.getextrema()!=(0,255) or sum(m.histogram()[1:255]): raise ValueError('INVALID_BINARY_MASK')
    diff=Image.composite(ImageChops.difference(a,b),Image.new('RGB',a.size),m)
    changed=sum(1 for p in diff.getdata() if p!=(0,0,0))
    return {'protected_pixels_preserved':changed==0,'changed_protected_pixels':changed,'identity_verified':False,'publication_allowed':False}
