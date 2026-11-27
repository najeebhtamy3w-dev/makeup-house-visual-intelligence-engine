"""OCR corroboration is not proof of SKU identity."""
from .identity_fusion import read_ocr,strong_lines,normalize,size_candidates,canonical_size

def assess_text(fields,lines):
    text=' '.join(strong_lines(lines))
    joined=normalize(text)
    brand=normalize(fields.get('brand'))
    sizes={canonical_size(s) for s in size_candidates(text)}
    expected=canonical_size(fields.get('size') or '')
    return {'brand_supported':bool(len(brand)>=3 and brand in joined),
            'size_supported':bool(expected and expected in sizes),
            'size_review_required':bool(expected and sizes and expected not in sizes),
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
