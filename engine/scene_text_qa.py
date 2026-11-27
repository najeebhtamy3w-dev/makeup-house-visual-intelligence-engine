"""OCR evidence only; never certifies product identity."""
import unicodedata
import re
from PIL import Image, ImageOps

def tokens(lines):
    return set(re.findall(r"\w+",unicodedata.normalize("NFKC"," ".join(lines)).casefold()))

def compare_text(source, output, placement, bounds, reader):
    with Image.open(source) as im:
        a=ImageOps.exif_transpose(im).convert("RGB").crop(tuple(bounds))
    x,y,w,h=placement
    with Image.open(output) as im:
        b=im.convert("RGB").crop((x,y,x+w,y+h))
    before=tokens(reader(a))
    after=tokens(reader(b))
    missing=sorted(before-after)
    return {"status":"REVIEW_REQUIRED" if not before or missing else "OCR_CORROBORATED",
            "missing_tokens":missing,"source_token_count":len(before),
            "identity_verified":False,"publication_allowed":False}
