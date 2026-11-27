# MH-VIE Intelligence Core V0.16 — provisional handover
Status: implementation checkpoint, NOT final acceptance.
Branch: feature/v015-search-integration.
Python entry point: engine.integration_core.discover(query, search, allowed_hosts, output, max_pages=5, max_images=20).
Use engine.search_discovery.SearxDiscovery with an operator-configured endpoint. Never accept arbitrary endpoints or allowed_hosts from mobile requests. Use a private per-job output directory.
Response schema 1.0: status, query, candidates, errors, attempts, publication_allowed. Candidate fields include sha256, width, height, file, source, url, quality, possible_duplicate_of, identity_verified, rights, publication_allowed.
All candidates require human review. Perceptual hashes are duplicate hints, not SKU proof.
Android must not run Python directly or assume a deployed API exists. Backend transport, authentication, job persistence and file serving remain to implement. Do not embed provider credentials in APK.
Existing OCR/Qwen acceptance: engine/blind_identity_acceptance.py; search is opt-in. Model inference is not identity approval.
Regression: python -m unittest discover -s tests. Existing CI installs Pillow and barcode dependencies. New integration tests use injected fixture downloader, not live internet.
Creative studio: see CREATIVE_STUDIO_ROADMAP.md. Generative inference, identity lock, GPU benchmark and production acceptance remain pending. No claim of complete model weights or APK.
Work can proceed independently with Android source recovery and UI contracts; final integration requires a verified backend and real-photo acceptance.
