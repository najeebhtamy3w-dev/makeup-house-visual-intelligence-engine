"""Conservative mask cleanup; ambiguous connected objects require human review."""
from PIL import Image
from collections import deque

def refine_mask(probability, threshold=128):
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
    binary=p.point(lambda v:255 if v>=threshold else 0)
    from PIL import ImageChops, ImageFilter
    binary=ImageChops.multiply(binary,support.filter(ImageFilter.MaxFilter(3)))
    bounds=binary.getbbox()
    hist=p.histogram()
    uncertain=sum(hist[64:192])/(w*h)
    flags=[]
    if len(components)>1 and len(components[1])>=largest*.005: flags.append("MULTIPLE_OBJECTS")
    if bounds and (bounds[0]==0 or bounds[1]==0 or bounds[2]==w or bounds[3]==h): flags.append("TOUCHES_FRAME")
    if uncertain>.08: flags.append("UNCERTAIN_BOUNDARY")
    return binary,{"components":len(components),"removed_preview_pixels":removed,"uncertain_fraction":uncertain,"flags":flags,"human_review_required":True}
