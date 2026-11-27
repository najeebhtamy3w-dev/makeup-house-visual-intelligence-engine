# Backend recovery and API security — V4 continuation

This increment retains the current FastAPI `/v1/inputs` and `/v1/batches` architecture. It does not restore the earlier experimental gateway or replace successful Android contracts.

## Implemented behavior

- Optional `Idempotency-Key` on `POST /v1/batches` accepts 1–128 characters. Repeating the same normalized jobs returns the original batch ID, including after restart. Reusing that key for different jobs returns HTTP 409 `IDEMPOTENCY_CONFLICT`.
- `POST /v1/batches/{batch_id}/cancel` returns `{ "cancelled": count }`. Queued and running jobs become `CANCELLED`. Inference cancellation is cooperative: a running model may finish, but its stale result cannot become a completed result. `/retry` also requeues cancelled jobs within the existing three-attempt cap.
- Runtime completion compares both state and attempt number. Recovery, cancellation or retry cannot be overwritten by an earlier attempt's late completion.
- The service worker acquires an exclusive Linux `fcntl` lease on `worker.lock` before initializing models. A second worker or recovery process fails with `WORKER_ALREADY_ACTIVE`. A new worker holding that lease marks interrupted tasks `FAILED / INTERRUPTED`; the operator/client can retry them explicitly. The `recover` CLI command acquires the same lease. This mechanism targets the current Linux backend; Windows portability is not implemented.
- Known availability/integrity errors preserve stable codes, including `IDENTITY_UNAVAILABLE`, `STUDIO_UNAVAILABLE`, `SEGMENTER_UNAVAILABLE` and `INPUT_HASH_MISMATCH`. Unexpected exception text remains private; responses retain only the exception class.
- `/v1/openapi.json` exposes the current OpenAPI contract only with the same Bearer authentication as the API. Interactive documentation remains disabled.

## Input and artifact integrity

Image uploads remain streamed and limited to 10 MB / 25 million pixels. JSON mutation requests are bounded to 1 MB before model parsing. Browser Origin headers are rejected; the intended client is the native application. API responses use `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`.

Before processing a stored input, `JobHandler` rejects symlinks and verifies its content SHA-256 against the input identifier. New job results include an `artifacts` map of filename, SHA-256 and byte count. Review ZIP archives have a separate SHA-256 in the persisted result.

Existing authenticated artifact routes are preserved:

- `/v1/batches/{batch_id}/jobs/{job_id}/files/{name}`
- `/v1/batches/{batch_id}/jobs/{job_id}/export`

Files must belong to the completed job's exact output directory, pass the filename allowlist and symlink/path checks, and match the persisted digest. Image files are additionally decoded/validated with the existing safe image inspector; downloads return their actual image MIME. Individual artifacts are bounded to 25 MB and ZIP exports to 250 MB. Cross-job access and modified files are rejected. A legacy PNG/ZIP result without a stored integrity manifest returns 409 and should be rerun; hash-named downloaded `.bin` files can still be verified from their filename.

## Operation

Continue using the existing documented environment configuration and commands:

```sh
python -m engine.service_main api
python -m engine.service_main worker
```

The API remains bound to `127.0.0.1:8765`. Use a trusted TLS reverse proxy for the Android HTTPS endpoint and keep the strong token private. This increment does not deploy a server, provision TLS, add paid resources, run model inference, or claim production acceptance.

The private data directory and SQLite database remain durable storage with no automatic expiry/deletion policy. Review files from cancelled attempts may remain private diagnostics; they are inaccessible through the completed-job download endpoints.

## Verification

Focused commands:

```sh
python -m unittest discover -s tests -p test_batch_runtime.py -v
python -m unittest discover -s tests -p test_service_api.py -v
python -m unittest discover -s tests -p test_workflow_end_to_end.py -v
python -m unittest discover -s tests -p test_scene_service_integration.py -v
```

Tests cover persisted idempotency/conflicts, cancellation, recovery/retry races, worker lease exclusivity, safe error exposure, authentication/OpenAPI, request limits, cross-job/traversal/symlink denial, modified input/artifact detection, and existing studio/scene upload-to-export workflows. Fixture model adapters prove control flow and integrity handling; they do not prove real generative model fidelity or live source search.
