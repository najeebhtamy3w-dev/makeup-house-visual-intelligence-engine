"""Low-cost visual signals, not SKU verification or learned aesthetics."""
from PIL import Image, ImageOps, ImageStat, ImageFilter

def signals(image):
    image = ImageOps.exif_transpose(image).convert('RGB')
    w,h = image.size
    gray = image.convert('L')
    small = gray.resize((9,8),Image.Resampling.LANCZOS)
    pixels = list(small.getdata())
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | int(pixels[y*9+x] > pixels[y*9+x+1])
    sample = gray.copy()
    sample.thumbnail((512,512))
    edge = sample.filter(ImageFilter.FIND_EDGES)
    return dict(width=w,height=h,dhash=f'{bits:016x}',
                edge_variance=round(ImageStat.Stat(edge).var[0],3),
                brightness=round(ImageStat.Stat(sample).mean[0],3),
                resolution_status='LOW_RESOLUTION' if min(w,h)<400 else 'RESOLUTION_CANDIDATE',
                sku_status='UNVERIFIED',aesthetic_status='NOT_EVALUATED')

def distance(a,b):
    return (int(a,16)^int(b,16)).bit_count()

def near_duplicate(a,b,threshold=4):
    if not 0 <= threshold <= 64:
        raise ValueError('INVALID_THRESHOLD')
    return distance(a,b)<=threshold
