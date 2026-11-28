# MH-VIE branch policy

- main: stable accepted releases and preserved historical experiments.
- feature/v015-search-integration: current V0.26 integration candidate; preserve history.
- development: historical development baseline; reconcile only through reviewed integration.
- Promote to main through reviewed PR after regression, live artifact inspection, and conflict review. No force pushes or deletion of historical evidence.
- GPU acceptance and Android acceptance remain separate gates. Work owns Android delivery.
- Search priority: Instagram indexed public posts, general web, optional direct editing. Segmentation is independent.
