import json
from pathlib import Path
from .deep_extraction import extract
from .safe_download import Downloader, inspect_image

PAGES = {
 'cerave': ['https://www.instagram.com/p/Df9S5mqjDod/', 'https://www.cerave.com/skincare/cleansers/hydrating-facial-cleanser'],
 'purador': ['https://www.instagram.com/reel/DJo2Pngy6u_/', 'https://purador.com/products/20vitamincserum'],
 'maybelline': ['https://www.instagram.com/p/Ded8vszCK6V/', 'https://www.maybelline.com/eye-makeup/mascara/lash-sensational-sky-high-washable-mascara-makeup']
}
def run(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    client = Downloader(['instagram.com','cdninstagram.com','cerave.com','purador.com','maybelline.com','cdn.shopify.com'])
    report = []
    for product, pages in PAGES.items():
        seen = set()
        for page in pages:
            try:
                raw, _, final = client.fetch(page, 5000000, 'text/html')
                candidates = extract(final, raw.decode('utf-8','replace'), 30)
                report.append(dict(product=product,source=page,status='CANDIDATES_FOUND' if candidates else 'NO_CANDIDATES_ON_PAGE',count=len(candidates)))
                for row in candidates:
                    row['product'] = product
                    try:
                        data, mime, url = client.fetch(row['url'], 10000000, 'image/')
                        row.update(inspect_image(data,mime), final_url=url)
                        digest = row['sha256']
                        if digest in seen:
                            row['status'] = 'DUPLICATE'
                        else:
                            seen.add(digest)
                            filename = product + '-' + digest + '.bin'
                            (output / filename).write_bytes(data)
                            row['file'] = filename
                    except Exception as e:
                        row.update(status='DOWNLOAD_OR_VALIDATION_FAILED',error=str(e))
                    report.append(row)
            except Exception as e:
                report.append(dict(product=product,source=page,status='SEARCH_INCOMPLETE',error=str(e)))
            (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

if __name__ == '__main__':
    run('results-v06')
