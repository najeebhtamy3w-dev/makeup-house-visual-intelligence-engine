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

## Concrete Linux deployment package

The `deploy/` directory now contains an operator-invoked preparation tool, strict configuration validator, two systemd units, a Caddy TLS template and an authenticated health smoke command. Nothing in this package deploys itself, creates a cloud resource, obtains a paid service, or downloads model weights. Preparation does not call `sudo`, `systemctl` or Caddy.

Prerequisites on the operator's Linux host: Python 3.11/3.12 with `venv` and pip, systemd, an installed Caddy service, an operator-owned domain pointing to that host, and an authorized SearXNG endpoint. The host needs outbound access to approved sources; automatic TLS needs inbound ports 80/443. Port 8765 stays on loopback. GPU/CUDA and model memory feasibility are separate checks.

1. Copy `deploy/backend.env.example` to a private file outside the repository, give it mode 600 and replace every `REPLACE_` value. Generate a random token locally, for example with `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`. Do not commit the completed environment file. Supply actual approved source domains rather than wildcard domains. Plain `KEY=value` syntax is required; quotes, shell expansion and executable expressions are rejected.
2. Use a new empty installation prefix outside `/home`, `/root` and `/tmp`, such as `/srv/mhvie-v4`. The systemd sandbox hides home and temporary directories. The caller must already have permission to create files in that prefix; the preparer never escalates privileges. An administrator can create a dedicated non-login account with `useradd --system --user-group --home-dir /nonexistent --shell /usr/sbin/nologin mhvie` and make the empty prefix writable to the preparing operator. These account/filesystem operations are explicit host administration steps, not executed by this package.
3. Validate first, then prepare:

```sh
python3 deploy/prepare.py --prefix /srv/mhvie-v4 --env /private/path/backend.env --user mhvie --check-only
python3 deploy/prepare.py --prefix /srv/mhvie-v4 --env /private/path/backend.env --user mhvie
```

The second command copies the backend source, creates a virtual environment, installs the pinned service dependencies plus lightweight barcode/numeric dependencies, runs `pip check`, checks backend imports, and renders the units/Caddy configuration. It writes `preparation.json` with the source commit and `deployed: false`. It refuses a nonempty prefix to preserve an existing installation. `--prepare-only` renders/copies without installing dependencies and reports `PREPARED_NOT_INSTALLED`; those files cannot be treated as a working service.

The preparer always sets `MHVIE_DATA` to the prefix's private `data` directory. Its environment file is mode 600. Optional model paths must already exist locally; this package does not install Torch/Paddle/Diffusers or claim those model profiles are ready. Leave OCR, segmentation and model paths disabled for the basic API/search installation. Enable them only after installing the separately tested ML profile, preparing local weights, checking their licenses and measuring the host resources. The worker's Hugging Face/Transformers settings enforce offline model loading. The service source, virtual environment and models are mounted read-only; only `data` and `cache` are writable within the service sandbox.

4. Before activation, an administrator sets ownership and traversal permissions. The installation root/source/venv/models should be owned by `root:mhvie` and readable/traversable by group `mhvie`; only `data` and `cache` should be owned and writable by `mhvie`. Keep `config/backend.env` owned by root with mode 600 (systemd reads it before launching the non-root service). A concrete starting sequence for this **new installation only** is:

```sh
sudo chown -R root:mhvie /srv/mhvie-v4
sudo chmod 750 /srv/mhvie-v4 /srv/mhvie-v4/source /srv/mhvie-v4/config /srv/mhvie-v4/models /srv/mhvie-v4/venv
sudo chmod -R g+rX /srv/mhvie-v4/source /srv/mhvie-v4/models /srv/mhvie-v4/venv
sudo chmod 600 /srv/mhvie-v4/config/backend.env
sudo chown -R mhvie:mhvie /srv/mhvie-v4/data /srv/mhvie-v4/cache
sudo chmod 700 /srv/mhvie-v4/data /srv/mhvie-v4/cache
sudo install -m 644 /srv/mhvie-v4/units/mhvie-api.service /etc/systemd/system/mhvie-api.service
sudo install -m 644 /srv/mhvie-v4/units/mhvie-worker.service /etc/systemd/system/mhvie-worker.service
sudo systemd-analyze verify /etc/systemd/system/mhvie-api.service /etc/systemd/system/mhvie-worker.service
sudo systemctl daemon-reload
sudo systemctl enable --now mhvie-api.service mhvie-worker.service
```

The ML worker always uses the configured non-root account. Do not run multiple worker services against this data directory. The persistent worker lease prevents simultaneous recovery/inference workers. Updating an existing host requires a fresh empty prefix plus a deliberate service-path switch, not overwriting live source or its data directory.

5. Review the rendered `config/Caddyfile`. It contains the actual configured domain and reverse-proxies only to `127.0.0.1:8765`; it contains no token. Merge that site block into the host's existing Caddy configuration without overwriting other sites, validate the **combined** configuration with `caddy validate`, then reload the Caddy service. Caddy's automatic TLS still requires working DNS/network access. No TLS certificate or live endpoint was created by preparing this package.
6. Verify local API and then HTTPS through the same authenticated smoke command:

```sh
sudo /srv/mhvie-v4/venv/bin/python /srv/mhvie-v4/source/deploy/smoke.py --env /srv/mhvie-v4/config/backend.env --url http://127.0.0.1:8765
sudo /srv/mhvie-v4/venv/bin/python /srv/mhvie-v4/source/deploy/smoke.py --env /srv/mhvie-v4/config/backend.env
```

The smoke command checks certificate validity for HTTPS, never follows redirects with the token, bounds its response, and never prints the token. Success means the authenticated API is reachable; `model_readiness: NOT_VERIFIED` remains an explicit model-acceptance limitation. Only after HTTPS succeeds should the operator enter that actual URL/token into the Android application.

Deployment-package verification: five local tests exercise configuration rejection, secret-free errors, safe non-root rendering, refusal to overwrite an existing prefix, and an actual loopback authenticated health exchange including redirect refusal. Both rendered systemd units passed `systemd-analyze verify` on the development Linux host with a temporary executable path. Caddy is unavailable in this development environment, so Caddy configuration validation, real TLS, host installation and external Android connectivity remain **NOT VERIFIED**. No package installation or service activation is performed by the deployment tests.
