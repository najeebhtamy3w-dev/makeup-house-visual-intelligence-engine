"""Run API and single worker separately with shared private data directory."""
import os
import time
import argparse
from pathlib import Path
from .batch_runtime import BatchRuntime

def main():
    p=argparse.ArgumentParser()
    p.add_argument('mode',choices=['api','worker','recover'])
    a=p.parse_args()
    root=Path(os.environ['MHVIE_DATA']).resolve()
    root.mkdir(parents=True,exist_ok=True)
    runtime=BatchRuntime(root/'jobs.sqlite3')
    if a.mode=='api':
        import uvicorn
        from .service_api import create_app
        uvicorn.run(create_app(runtime,root,os.environ['MHVIE_TOKEN']),host='127.0.0.1',port=8765)
    elif a.mode=='recover':
        print(runtime.recover_interrupted())
    else:
        from .job_handler import JobHandler
        from .search_discovery import SearxDiscovery
        editor=segmenter=None
        if os.environ.get('MHVIE_EDIT_MODEL'):
            from .creative_studio import LocalEditor
            from .product_lock import BackgroundSegmenter
            editor=LocalEditor(os.environ['MHVIE_EDIT_MODEL'],os.environ['MHVIE_EDIT_BACKEND'])
            segmenter=BackgroundSegmenter()
        handler=JobHandler(root,SearxDiscovery(os.environ['MHVIE_SEARX']),os.environ['MHVIE_HOSTS'].split(','),editor,segmenter)
        while True:
            if runtime.run_next(handler) is None: time.sleep(1)

if __name__=='__main__':
    main()
