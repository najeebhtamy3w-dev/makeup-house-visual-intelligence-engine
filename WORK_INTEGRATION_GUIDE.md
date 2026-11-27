# MH-VIE integration candidate
Status: implementation in progress; not accepted for production.

Android must use the private backend over TLS, not embed model weights or a shared permanent token in the APK. Provision credentials separately.
Run API and worker separately using python -m engine.service_main api / worker. Both use MHVIE_DATA. API requires MHVIE_TOKEN. Worker requires MHVIE_SEARX and MHVIE_HOSTS. Optional model settings are in MODEL_REGISTRY.json.
Upload raw image bytes to POST /v1/inputs. Submit jobs to POST /v1/batches with kinds identify, discover, studio. Poll GET /v1/batches/{batch_id}. Retrieve completed job files using /v1/batches/{batch_id}/jobs/{job_id}/files/{name}. Retry failed jobs using POST /v1/batches/{batch_id}/retry.
All requests require Bearer authentication. COMPLETED means processing completed, not verified identity or approved rights.
Brand profiles and private review export are library modules; API wiring pending. No model weights bundled. GPU compatibility, dependency lock, deployment, live provider tests, rights review and Android acceptance remain pending.
