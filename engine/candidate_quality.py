"""Image quality evidence, not product identity or rights approval."""
from PIL import Image, ImageOps, ImageFilter
import hashlib

def assess(path):
    with Image.open(path) as source:
        if source.width*source.height>25000000:
            raise ValueError('PIXEL_LIMIT')
        image=ImageOps.exif_transpose(source).convert('RGB')
        w,h=image.size
        gray=ImageOps.grayscale(image)
        small=gray.resize((9,8))
        pixels=list(small.getdata())
        bits=0
        for y in range(8):
            for x in range(8):
                bits=(bits<<1)|int(pixels[y*9+x]>pixels[y*9+x+1])
        return {'width':w,'height':h,'resolution_ok':min(w,h)>=600,
                'dhash':format(bits,'016x'),'identity_verified':False,
                'rights':'RIGHTS_UNVERIFIED','status':'REVIEW_REQUIRED'}

def distance(a,b):
    return (int(a,16)^int(b,16)).bit_count()
