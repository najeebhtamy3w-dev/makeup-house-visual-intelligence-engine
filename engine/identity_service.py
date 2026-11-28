from PIL import Image, ImageOps
from .identity_fusion import read_ocr
from .adaptive_identity import identify_adaptive
from collections import OrderedDict
from copy import deepcopy
import hashlib
import time
from .photo_workflow import read_barcodes
from .catalog_evidence import collect_catalog
from .barcode_priority import valid_gtins, matching_evidence

class IdentityService:
    def __init__(self,reader,model,search=None,downloader=None):
        self.reader=reader
        self.model=model
        self.search=search
        self.downloader=downloader
        self.cache=OrderedDict()
    def __call__(self,path):
        start=time.monotonic()
        codes=read_barcodes(path)
        gtins=valid_gtins(codes)
        evidence=[]
        barcode_error=None
        if len(gtins)==1 and self.search is not None and self.downloader is not None:
            try:
                hits=list(self.search(gtins[0]))[:3]
                evidence=matching_evidence(collect_catalog(hits,self.downloader)['evidence'],gtins[0])
            except Exception as exc:
                barcode_error=type(exc).__name__
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
        result=identify_adaptive(lines,lambda:self.model.identify(image),search=self.search,catalog_downloader=self.downloader,structured_evidence=evidence)
        result['barcodes']=codes
        result['barcode_evidence']={'gtins':gtins,'matches':len(evidence),'error':barcode_error}
        result['ocr_lines']=lines
        result['publication_allowed']=False
        result['performance']={'ocr_cache_hit':hit,'ocr_seconds':ocr_seconds,'total_seconds':time.monotonic()-start}
        return result
