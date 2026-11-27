"""Run both configured local editors in separate processes; no implicit downloads."""
import argparse,json,subprocess,sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    for key in ('photos','flux','qwen','output','clip-weights'):
        p.add_argument('--'+key,required=True)
    a=p.parse_args()
    photos=sorted(x for x in Path(a.photos).rglob('*') if x.suffix.lower() in ('.jpg','.jpeg','.png','.webp'))
    if len(photos)!=10: raise SystemExit('EXACTLY_TEN_REFERENCE_PHOTOS_REQUIRED')
    root=Path(a.output)
    root.mkdir(parents=True,exist_ok=True)
    reports=[]
    prompt='Create a premium cosmetic advertising photograph with elegant lighting and a clean background. Preserve the exact package, logo, printed text, color and shape.'
    for backend in ('flux','qwen'):
        for i,source in enumerate(photos):
            output=root/f'{backend}-{i+1:02}.png'
            cmd=[sys.executable,'-m','engine.studio_benchmark','--backend',backend,'--model-dir',getattr(a,backend),'--source',str(source),'--output',str(output),'--prompt',prompt,'--seed','42','--clip-weights',a.clip_weights,'--ocr']
            try:
                subprocess.run(cmd,check=True,timeout=1800)
                reports.append(json.loads(Path(str(output)+'.json').read_text()))
            except (subprocess.SubprocessError,OSError,ValueError) as exc:
                reports.append({'backend':backend,'source':str(source),'error':type(exc).__name__})
            (root/'comparison.json').write_text(json.dumps(reports,indent=2))
    if any('error' in r for r in reports): raise SystemExit('GPU_BENCHMARK_INCOMPLETE')
if __name__=='__main__': main()
