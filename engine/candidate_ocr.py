"""OCR corroboration is not proof of SKU identity."""
from .identity_fusion import read_ocr,strong_lines,normalize,size_candidates,canonical_size
import re
from .barcode_priority import canonical_gtin
from .sku_evidence import norm as text_norm,size as parse_size

def supported(text,value):
    words=text_norm(value or '')
    return bool(words and re.search(r'(?<!\w)'+re.escape(words)+r'(?!\w)',text))

def assess_text(fields,lines):
    text=' '.join(strong_lines(lines))
    joined=text_norm(text)
    brand=text_norm(fields.get('brand'))
    def quantity(value):
        parsed=parse_size(value)
        return format(parsed[0].normalize(),'f')+parsed[1] if parsed else None
    found=re.findall(r'\d+(?:[.,]\d+)?\s*(?:ml|kg|g|l|كجم|غرام|جم|مل|لتر)\b',text.casefold())
    sizes={quantity(s) for s in found}-{None}
    expected=quantity(fields.get('size') or '')
    expected_code=canonical_gtin(fields.get('gtin') or fields.get('barcode'))
    codes={canonical_gtin(x) for x in re.findall(r'(?<!\d)\d{8,14}(?!\d)',text)}-{None}
    dimensions={k:supported(joined,fields.get(k)) for k in ('name','variant','shade','concentration','formula') if fields.get(k)}
    return {'brand_supported':supported(joined,brand),
            'name_supported':dimensions.get('name',False),
            'required_text_supported':all(dimensions.values()) and 'name' in dimensions,
            'text_dimensions':dimensions,
            'gtin_supported':bool(expected_code and codes=={expected_code}),
            'gtin_conflict':bool(expected_code and codes and codes!={expected_code}),
            'observed_gtins':sorted(codes),
            'size_supported':bool(expected and expected in sizes),
            'size_review_required':bool(expected and sizes and sizes!={expected}),
            'observed_sizes':sorted(sizes),'lines':lines,'identity_verified':False}

def evaluate_candidate(path,fields,reader):
    from tempfile import TemporaryDirectory
    from pathlib import Path
    from PIL import Image,ImageOps
    with TemporaryDirectory() as d:
        target=Path(d)/'candidate.png'
        with Image.open(path) as im:
            if im.width*im.height>25000000: raise ValueError('PIXEL_LIMIT')
            ImageOps.exif_transpose(im).convert('RGB').save(target)
        return assess_text(fields,read_ocr(target,reader))
