from PIL import ImageOps, ImageChops
from .mask_quality import refine_mask

def adaptive_mask(image,segmenter,threshold=128):
    probability=segmenter.segment(image).convert("L")
    if probability.size!=image.size: raise ValueError("MASK_SIZE_MISMATCH")
    first,quality=refine_mask(probability,threshold)
    report={"passes":1,"quality":quality,"selection":"PRIMARY","mask_verified":False}
    if quality["flags"]:
        # Flip consistency exposes unstable predictions without another model download.
        try:
            other=ImageOps.mirror(segmenter.segment(ImageOps.mirror(image)).convert("L"))
            if other.size!=image.size: raise ValueError("MASK_SIZE_MISMATCH")
            second,q2=refine_mask(other,threshold)
            union=ImageChops.lighter(first,second).histogram()[255]
            intersection=ImageChops.darker(first,second).histogram()[255]
            report.update(passes=2,consistency_iou=intersection/max(1,union),secondary_quality=q2)
            if report["consistency_iou"]<.9:
                report["quality"]["flags"].append("UNSTABLE_SEGMENTATION")
            # Do not automatically discard ambiguous product pixels.
        except Exception as exc:
            report["secondary_error"]=type(exc).__name__
    bounds=first.getbbox()
    if bounds:
        x0,y0,x1,y1=bounds
        report["bounding_box"]=list(bounds)
        report["foreground_fraction"]=first.histogram()[255]/(first.width*first.height)
        report["frame_clearance_pixels"]=min(x0,y0,first.width-x1,first.height-y1)
        report["review_required"]=True
    return first,report
