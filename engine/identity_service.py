from PIL import Image, ImageOps
from .identity_fusion import read_ocr
from .adaptive_identity import identify_adaptive
from collections import OrderedDict
from copy import deepcopy
import hashlib
import time

class IdentityService:
    def __init__(self,reader,model,search=None,downloader=None):
        self.reader=reader
        self.model=model
        self.search=search
        self.downloader=downloader
        self.cache=OrderedDict()
    def __call__(self,path):
        start=time.monotonic()
        with Image.open(path) as im:
            if im.width*im.height>25000000: raise ValueError('PIXEL_LIMIT')
            image=ImageOps.exif_transpose(im).convert('RGB')
        key=hashlib.sha256(str(image.size).encode()+image.tobytes()).hexdigest()
        hit=key in self.cache
        t=time.monotonic()
        if hit:
            lines=deepcopy(self.cache[key])
            self.cache.move_to_end(key)
        else:
            lines=read_ocr(path,self.reader)
            self.cache[key]=deepcopy(lines)
            if len(self.cache)>64: self.cache.popitem(last=False)
        ocr_seconds=time.monotonic()-t
        result=identify_adaptive(lines,lambda:self.model.identify(image),search=self.search,catalog_downloader=self.downloader)
        result['ocr_lines']=lines
        result['publication_allowed']=False
        result['performance']={'ocr_cache_hit':hit,'ocr_seconds':ocr_seconds,'total_seconds':time.monotonic()-start}
        return result
