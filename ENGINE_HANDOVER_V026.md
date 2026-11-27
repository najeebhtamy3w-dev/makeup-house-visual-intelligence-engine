# MH-VIE V0.26 engine handover — candidate, not accepted
## Scope
Independent image engine; Android UI/build belongs to Work. Do not replace the recovered search provider or make segmentation mandatory.
## Worker configuration
Python service: python -m engine.service_main worker; API: python -m engine.service_main api.
Required operator configuration: MHVIE_DATA, MHVIE_TOKEN (API), MHVIE_SEARX, MHVIE_HOSTS (worker).
Optional: MHVIE_CLIP_WEIGHTS, MHVIE_AESTHETIC_WEIGHTS, MHVIE_AESTHETIC_SHA256, MHVIE_VISION_MODEL, MHVIE_OCR=1, MHVIE_SEGMENTATION=1, MHVIE_FLUX_MODEL, MHVIE_QWEN_EDIT_MODEL, MHVIE_EDIT_BACKEND. Legacy MHVIE_EDIT_MODEL remains supported.
One resident generative model per worker; switching requires restart. No mandatory paid API.
## Routing
Instagram indexed public posts first, general web second, optional direct_edit by user choice. No CAPTCHA bypass. Candidate evidence is not verified identity or publication permission.
Independent jobs: discover, smart_discover, photo_discover, identify, barcode, direct_edit, prepare_mask, correct_mask, locked_scene, studio. See engine/service_api.py for actual request schemas.
## Acceptance gates (not yet verified)
- Full regression at final commit.
- Inspect live discovery reports and downloaded images; verify Instagram source separately.
- Real reference photo comparison with OpenCLIP and LAION.
- Same ten real photos, identical prompts and seeds, FLUX vs Qwen; report latency, VRAM, text and visual identity review. GPU required; do not substitute synthetic tests.
- Review actual segmentation masks, especially hands and clipped packaging.
- Review PR conflicts and merge only after acceptance.
- Work: Android integration, device tests and debug APK; no production signing yet.
