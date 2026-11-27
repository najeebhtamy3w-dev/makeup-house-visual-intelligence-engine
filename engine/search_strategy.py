def queries(name):
    name=' '.join(name.split())
    return [name, name+' official product packaging', name+' cosmetic advertising campaign', name+' product texture swatch']

def coverage(rows):
    categories=set()
    for row in rows:
        if row.get('status')!='NEEDS_MANUAL_REVIEW' or min(row.get('width',0),row.get('height',0))<400:
            continue
        if row.get('possible_duplicates'):
            continue
        category=row.get('classification',{}).get('category_suggestion')
        if category in ('PACKSHOT','MARKETING'):
            categories.add(category)
    return categories

def complete(rows):
    return coverage(rows)=={'PACKSHOT','MARKETING'}
