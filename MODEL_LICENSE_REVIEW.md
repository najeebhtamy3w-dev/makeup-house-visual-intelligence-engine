# Model license acceptance register
Status: PENDING VERIFICATION. No commercial clearance granted.
For each deployed weight file record exact upstream repository, immutable revision, SHA256, license text and notices, redistribution conditions, reviewer and decision.
| Component | Upstream evidence to review |
|---|---|
| PaddleOCR | https://github.com/PaddlePaddle/PaddleOCR |
| Qwen vision | https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct |
| OpenCLIP | https://github.com/mlfoundations/open_clip |
| LAION aesthetic | https://github.com/LAION-AI/aesthetic-predictor |
| BiRefNet | https://github.com/ZhengPeng7/BiRefNet |
| Qwen edit | https://huggingface.co/Qwen/Qwen-Image-Edit-2511 |
| FLUX edit | https://huggingface.co/black-forest-labs/FLUX.2-klein-4B |
Code licenses do not automatically cover checkpoints. Verify exact weight provenance separately. No model redistribution in APK until reviewed. Image rights are separate.
Dependency acceptance: resolve each runtime profile on its target platform, run pip check, capture pip freeze and hashes, scan vulnerabilities, and repeat inference acceptance with the resolved environment.

## 2026-11-27 review decision
- BLOCK commercial deployment of Qwen2.5-VL-3B-Instruct revision 1b989f2c63999d7344135894d3cfa8f494116743. Exact license: https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/blob/1b989f2c63999d7344135894d3cfa8f494116743/LICENSE . Research only; commercial permission required. Preserve historical evaluation evidence; replace and rebenchmark before production.
- Qwen Image Edit 2511: upstream model card declares Apache-2.0 https://huggingface.co/Qwen/Qwen-Image-Edit-2511 . Eligible subject to exact snapshot and notices review.
- FLUX.2 klein 4B: Apache-2.0 license at https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/blob/e7b7dc27f91d/LICENSE.md . Eligible subject to exact snapshot and notices review. Do not substitute other variants without review.
- BiRefNet upstream model card declares MIT https://huggingface.co/ZhengPeng7/BiRefNet ; exact rembg ONNX asset provenance pending.
- Other weights and dependency audit remain pending. No production release authorized.
