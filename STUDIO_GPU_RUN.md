# Real studio GPU acceptance

Use an authorized GPU environment with BF16 support and sufficient RAM/VRAM. No paid runner is provisioned by this repository. Install compatible PyTorch CUDA, diffusers with Flux2KleinPipeline, transformers, accelerate, Pillow and rembg[cpu]. Record pip freeze and pip check. Obtain the exact reviewed FLUX.2-klein-4B snapshot locally; record revision and weight hashes. Do not substitute another variant without license review.

From the repository root:

```sh
python -m engine.studio_acceptance --backend flux --model-dir /path/to/local/model --source /path/to/real-product.jpg --output studio-real-result
```

Use a new output directory each time. Inspect mask.png, result.png and report.json. A successful run requires real inference and zero changed protected pixels. Human review must verify complete product coverage, label integrity, background quality and rights. Repeat with Qwen only if needed for quality or feasibility. Never treat a fixture as real generation. The GPU run is pending; no production acceptance is implied.


## V4 grouped comparison

After unpacking the existing blind10 archive, provide its original hash manifest:

```sh
python -m engine.gpu_acceptance --photos acceptance/blind10 --manifest acceptance/blind10/manifest.json --flux /approved/models/flux --qwen /approved/models/qwen --output gpu-comparison --clip-weights /approved/models/clip.pt --ocr
```

Each backend is one independent process, with one editor load for ten photos. The existing single-image studio_benchmark CLI remains supported. Preinstall and review the OCR/model caches before enabling inference; no paid GPU is provisioned. Qwen requires the documented native BF16 profile; T4 FLUX uses FP16. Missing models yield twenty explicit BLOCKED rows, not inference success. Current local preflight completed no generation.
