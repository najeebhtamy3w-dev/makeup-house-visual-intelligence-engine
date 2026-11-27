# MH-VIE V4 source recovery and reconciliation

Recovery performed 2026-11-28. This is an engineering candidate, not V1.0 acceptance.

| Source | Verified head | Disposition |
|---|---|---|
| main | 00805e863db60a639a1ef34aa3b52cb7512604d6 | Preserved; no release acceptance inferred |
| development / V0.14.2 | 2b4a610d5fc9ee6ee119277b7e91b876f3893137 | Historical ancestor, not current engine |
| feature/v015-search-integration / V0.27 | d5e7360421c61e6a57aece68dc72342792c91423 | Current integration base |
| recovery/v0142-before-v015 | 2b4a610d5fc9ee6ee119277b7e91b876f3893137 | Existing recovery point retained |
| recovery/v027-before-v4-integration | d5e7360421c61e6a57aece68dc72342792c91423 | Created before V4 changes |
| Draft PR #1 | feature/v015-search-integration → main | Still draft; quality/device gates not accepted |

## Previous Work session

The earlier session wrote uncommitted Android foundation and Python changes, but did not finish an APK, commit those changes, or deliver a durable source archive before interruption. The execution environment was recreated; neither that checkout nor its temporary tools remain. Scoped recovery searches found no MH-VIE source/APK archive containing those changes. They cannot honestly be reported as recovered source.

The original recovered Android application **is** present in Git, including its Kotlin engines, repository, Compose navigation, package identity and original archive. Its five previously identified UI/ViewModel files were still empty at the verified remote head. V4 restores these missing seams in the original application; it does not replace Android with the prior separate foundation flavor. Existing cloud providers remain preserved. The new backend already supersedes the old proposed gateway and is retained.

## Functional reconciliation

- Keep current Instagram-first `priority_discovery`, SearXNG, IPv4 public-address selection, downloader SSRF/TLS checks and recovered live probes.
- Keep current FastAPI `/v1/inputs` and `/v1/batches` contract; adapt Android to it rather than introduce the earlier `/v1/jobs` protocol.
- Keep `direct_edit` independent of masks and preserve optional protected editing, BiRefNet, correction and locked scenes.
- Keep OCR-first/lazy identity, OpenCLIP/LAION, candidate OCR and product-page evidence as separate signals.
- Strengthen candidate-image evidence: matching page metadata plus cosine cannot by itself corroborate every extracted image. Require candidate-level text or a valid matching GTIN; preserve missing/contradictory fields for review.
- Preserve commercial rights and identity approval as separate gates. No automatic publication.

## Recovered evidence

Run 46066676176 / artifact 15230604727 was recovered without repeating inference or search. Its 57 downloaded image files all match their SHA-256 filenames. The artifact contains three discovery reports and an OCR report. It is historical inference evidence, not a fresh run against V4.

The current `calibration_labels.json` was recovered separately; baseline measurements are recorded in `docs/CLASSIFICATION_BASELINE_57.json`. The known low selective accuracy and incomplete class coverage remain unresolved acceptance gates. No independent dataset is invented.

## Integration policy

Changes are integrated on the existing feature branch in bounded tested commits. No blind merge, force push, hard reset, archive downgrade or engine replacement is used. Main merge and V1.0 remain conditional on component quality, live workflows and device evidence; successful fixture tests alone do not satisfy those gates.

## Subsequent continuation recovery

The execution workspace was recreated again on continuation. Source commit ff3f5d433a582fbcb2c39ad36733188732d28c1e, Android CI artifact 15234185112 and the privately retained engineering key were recovered. The actual APK was re-signed with the same engineering certificate and durably retained. The native-decoder test fix and a supported Lint UAST compatibility setting are being verified in fresh CI; no detector or assertion is disabled. The grouped GPU runner was restored as a bounded extension with three lifecycle/hash regressions. The current saved-source gate is 156 passing tests, distinct from the earlier transient 159-test state. No transient output is represented as a saved final deliverable.
