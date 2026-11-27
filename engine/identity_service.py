from PIL import Image, ImageOps
from .identity_fusion import read_ocr
from .adaptive_identity import identify_adaptive

class IdentityService:
    def __init__(self,reader,model,search=None,downloader=None):
        self.reader=reader
        self.model=model
        self.search=search
        self.downloader=downloader
    def __call__(self,path):
        with Image.open(path) as im:
            if im.width*im.height>25000000: raise ValueError('PIXEL_LIMIT')
            image=ImageOps.exif_transpose(im).convert('RGB')
        lines=read_ocr(path,self.reader)
        result=identify_adaptive(lines,lambda:self.model.identify(image),search=self.search,catalog_downloader=self.downloader)
        result['ocr_lines']=lines
        result['publication_allowed']=False
        return result
