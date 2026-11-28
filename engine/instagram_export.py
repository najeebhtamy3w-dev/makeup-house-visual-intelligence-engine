"""Export only explicitly selected, locally downloaded Instagram candidates."""
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from PIL import Image
from .priority_discovery import instagram_post

def export_selected(root, report, selections, destination):
    root=Path(root).resolve()
    if not 1<=len(selections)<=2000:
        raise ValueError("INVALID_SELECTION_COUNT")
    manifest=[]
    seen=set()
    with ZipFile(destination,"w",ZIP_DEFLATED) as archive:
        for index,digest in selections:
            if type(index) is not int or not 0<=index<len(report) or not re.fullmatch(r"[a-f0-9]{64}",digest):
                raise ValueError("INVALID_SELECTION")
            if (index,digest) in seen:
                continue
            seen.add((index,digest))
            row=next((r for r in report[index]["candidates"] if r["sha256"]==digest),None)
            if row is None or not instagram_post({"url":row["source"]}):
                raise ValueError("INVALID_SOURCE")
            path=(root/str(index)/(digest+".bin")).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError("MISSING_IMAGE")
            data=path.read_bytes()
            if hashlib.sha256(data).hexdigest()!=digest:
                raise ValueError("HASH_MISMATCH")
            with Image.open(path) as im:
                ext={"JPEG":"jpg","PNG":"png","WEBP":"webp"}.get(im.format)
                if ext is None:
                    raise ValueError("UNSUPPORTED_FORMAT")
                im.verify()
            name=f"{index+1:03d}/{digest}.{ext}"
            archive.writestr(name,data)
            manifest.append({"file":name,"query":report[index]["query"],"source":row["source"],"sha256":digest,"publication_allowed":False})
        archive.writestr("manifest.json",json.dumps(manifest,ensure_ascii=False,indent=2))
    return manifest
