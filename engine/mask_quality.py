"""Conservative mask cleanup; ambiguous connected objects require human review."""
from PIL import Image
from collections import deque

def refine_mask(probability, threshold=128, *, preserve_details=False):
    p=probability.convert("L")
    w,h=p.size
    if w*h>25000000: raise ValueError("PIXEL_LIMIT")
    # Analyze topology on a bounded preview, preserving original resolution.
    preview=p.copy()
    preview.thumbnail((768,768),Image.Resampling.BILINEAR)
    a,b=preview.size
    data=bytearray(1 if v>=threshold else 0 for v in preview.getdata())
    labels=bytearray(a*b)
    components=[]
    for i in range(a*b):
        if not data[i]: continue
        data[i]=0
        q=deque([i]); pixels=[]
        while q:
            j=q.popleft(); pixels.append(j)
            x,y=j%a,j//a
            for k in (j-1 if x else -1,j+1 if x<a-1 else -1,j-a if y else -1,j+a if y<b-1 else -1):
                if k>=0 and data[k]:
                    data[k]=0; q.append(k)
        components.append(pixels)
    components.sort(key=len,reverse=True)
    if not components: raise ValueError("EMPTY_MASK")
    largest=len(components[0])
    # Remove only tiny disconnected specks; retain ambiguous larger parts.
    removed=0
    for comp in components:
        if len(comp)<max(3,largest*.005):
            removed+=len(comp)
        else:
            for j in comp: labels[j]=255
    support=Image.frombytes("L",(a,b),bytes(labels)).resize((w,h),Image.Resampling.NEAREST)
    threshold_mask=p.point(lambda v:255 if v>=threshold else 0)
    binary=threshold_mask
    from PIL import ImageChops, ImageFilter
    binary=ImageChops.multiply(binary,support.filter(ImageFilter.MaxFilter(3)))
    foreground_pixels=threshold_mask.histogram()[255]
    cleanup_removed=ImageChops.subtract(threshold_mask,binary).histogram()[255]
    # A preview cannot reliably distinguish a thin cap/stem from missing support.
    # Explicit conservative mode falls back to the original full-res threshold;
    # no expensive full-resolution graph walk or guessed product geometry.
    substantial_loss=cleanup_removed>max(3,foreground_pixels*.0005)
    detail_protection_applied=preserve_details and substantial_loss
    if detail_protection_applied:
        binary=threshold_mask
    bounds=binary.getbbox()
    hist=p.histogram()
    uncertain=sum(hist[64:192])/(w*h)
    flags=[]
    if substantial_loss: flags.append("DETAIL_LOSS_REVIEW_REQUIRED")
    if len(components)>1 and len(components[1])>=largest*.005: flags.append("MULTIPLE_OBJECTS")
    if bounds and (bounds[0]==0 or bounds[1]==0 or bounds[2]==w or bounds[3]==h): flags.append("TOUCHES_FRAME")
    if uncertain>.08: flags.append("UNCERTAIN_BOUNDARY")
    return binary,{"components":len(components),"threshold_foreground_pixels":foreground_pixels,
                   "cleanup_removed_foreground_pixels":cleanup_removed,
                   "removed_foreground_pixels":0 if detail_protection_applied else cleanup_removed,
                   "detail_protection_applied":bool(detail_protection_applied),"removed_preview_pixels":removed,"uncertain_fraction":uncertain,"flags":flags,"human_review_required":True}
