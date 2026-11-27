# MH-VIE integration candidate 0.25.0-rc1
Not production accepted. Private backend over TLS; never embed a permanent shared token in APK.
Run API and single worker separately: python -m engine.service_main api / worker. Shared MHVIE_DATA. API MHVIE_TOKEN; worker MHVIE_SEARX and MHVIE_HOSTS. Model settings in MODEL_REGISTRY.json.
All requests use Bearer authentication. Upload raw image bytes POST /v1/inputs. Submit POST /v1/batches with {"jobs":[...]}; poll GET /v1/batches/{batch_id}. Completed means processing, not rights or identity approval.
Jobs: identify, discover, barcode, smart_discover, photo_discover, prepare_mask, correct_mask, locked_scene, studio (experimental legacy).
## Recommended studio flow
1. Upload source image, retain returned input ID.
2. Submit {"kind":"prepare_mask","input":"SOURCE_ID"}.
3. Fetch mask.png and preview.png from /v1/batches/{batch_id}/jobs/{job_id}/files/{name}. Source dimensions in result.source_size. Preview coordinates must be mapped to original EXIF-normalized dimensions.
4. Upload mask.png as a new input. Optionally submit {"kind":"correct_mask","input":"SOURCE_ID","mask_input":"MASK_ID","strokes":[{"mode":"erase","radius":10,"points":[[100,200],[110,205]]}]}. Restore mode adds pixels. Repeat review as necessary. Download and re-upload latest mask.
5. Only after operator review submit {"kind":"locked_scene","input":"SOURCE_ID","mask_input":"MASK_ID","mask_reviewed":true,"prompt":"beige marble studio","brand":"makeup_house","formats":["square","story"]}.
6. Download edited.png and optional formats. Review text_qa, protected_pixels_preserved and mask. Formats may resample pixels and need separate review. Export ZIP via /v1/batches/{batch_id}/jobs/{job_id}/export.
The mask_reviewed flag is an operator assertion, not proof of correct segmentation. Frame-touching products require a complete source image. No automatic publication. OCR is optional and does not certify identity. FLUX is required for locked_scene; T4 uses FP16. No weights bundled.
## Acceptance
Fixture regression, live search, real segmentation and generation, license checks, deployment security and Android device acceptance must be verified before release. Do not label this candidate production-ready.
