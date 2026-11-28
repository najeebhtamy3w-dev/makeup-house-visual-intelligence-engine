def canonical_gtin(value):
    if not isinstance(value,str) or len(value) not in (8,12,13,14) or not value.isascii() or not value.isdigit():
        return None
    if not any(c!='0' for c in value):
        return None
    total=sum(int(c)*(3 if i%2==0 else 1) for i,c in enumerate(reversed(value[:-1])))
    return value.zfill(14) if (total+int(value[-1]))%10==0 else None

def valid_gtins(codes):
    return sorted({g for c in codes if (g:=canonical_gtin(c.get('text'))) is not None})

def matching_evidence(evidence,gtin):
    return [item for item in evidence if canonical_gtin(item.get('fields',{}).get('gtin'))==gtin]
