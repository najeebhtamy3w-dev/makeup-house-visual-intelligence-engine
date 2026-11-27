"""Explicit operator decisions; no automatic license inference."""
import re
from datetime import datetime, timezone

def decision(digest, source, reviewer, evidence, *, commercial=False, derivatives=False, sku_confirmed=False):
    if not re.fullmatch(r'[0-9a-f]{64}',digest) or not all(isinstance(x,str) and x.strip() for x in (source,reviewer,evidence)):
        raise ValueError('INVALID_RIGHTS_RECORD')
    return dict(sha256=digest,source=source,reviewer=reviewer,evidence=evidence,commercial=commercial is True,derivatives=derivatives is True,sku_confirmed=sku_confirmed is True,recorded_at=datetime.now(timezone.utc).isoformat())

def permitted(record,digest,source,*,derivative=False):
    return bool(record and record.get('sha256')==digest and record.get('source')==source and all(record.get(k) is True for k in ('commercial','sku_confirmed')) and record.get('reviewer') and record.get('evidence') and (not derivative or record.get('derivatives') is True))
