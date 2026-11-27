from PIL import Image, ImageOps, ImageDraw
from pathlib import Path
import hashlib

def correct_mask(source,mask,output,strokes):
    with Image.open(source) as im:
        if im.width*im.height>25000000: raise ValueError("PIXEL_LIMIT")
        original=ImageOps.exif_transpose(im).convert("RGB")
    with Image.open(mask) as im:
        m=im.convert("L")
    if m.size!=original.size or sum(m.histogram()[1:255]): raise ValueError("INVALID_MASK")
    if not 1<=len(strokes)<=100: raise ValueError("STROKE_LIMIT")
    w,h=m.size
    draw=ImageDraw.Draw(m)
    for stroke in strokes:
        points=stroke["points"]; radius=stroke["radius"]; mode=stroke["mode"]
        if mode not in ("erase","restore") or not 1<=radius<=256 or not 1<=len(points)<=256: raise ValueError("INVALID_STROKE")
        if any(not (0<=x<w and 0<=y<h) for x,y in points): raise ValueError("OUTSIDE_IMAGE")
        color=0 if mode=="erase" else 255
        if len(points)>1: draw.line([tuple(p) for p in points],fill=color,width=radius*2,joint="curve")
        for x,y in points: draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=color)
    if m.getextrema()!=(0,255): raise ValueError("INVALID_CORRECTED_MASK")
    output=Path(output)
    with output.open("xb") as f: m.save(f,format="PNG")
    preview_mask(source,output,output.with_name("preview.png"))
    return {"status":"MASK_REVIEW_REQUIRED","mask_verified":False,"sha256":hashlib.sha256(output.read_bytes()).hexdigest(),"source_size":[w,h]}

def preview_mask(source,mask,output):
    with Image.open(source) as im: original=ImageOps.exif_transpose(im).convert("RGB")
    with Image.open(mask) as im: m=im.convert("L")
    if m.size!=original.size: raise ValueError("MASK_SIZE_MISMATCH")
    original.thumbnail((768,768),Image.Resampling.LANCZOS)
    m=m.resize(original.size,Image.Resampling.NEAREST)
    preview=Image.composite(original,Image.new("RGB",original.size,(190,190,190)),m)
    with Path(output).open("xb") as f: preview.save(f,format="PNG")
