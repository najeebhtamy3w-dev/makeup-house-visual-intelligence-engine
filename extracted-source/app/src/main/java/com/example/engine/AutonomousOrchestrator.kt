package com.example.engine

import android.content.Context
import android.util.Log
import com.example.core.EngineSettings
import com.example.core.SecurityAndImageUtils
import com.example.data.MhvieRepository
import com.example.model.BatchJob
import com.example.model.BatchStatus
import com.example.model.BrandProfile
import com.example.model.DiscoveredImage
import com.example.model.EngineConfig
import com.example.model.ImageCategory
import com.example.model.ProductRecord
import com.example.model.ProductStatus
import com.example.model.ReviewDecision
import com.example.model.RightsStatus
import com.example.model.SearchStrategy
import com.example.model.ZeroResultReason
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import kotlinx.coroutines.withContext

data class OrchestratorProgress(
    val activeBatchId: String? = null,
    val activeProductTitle: String = "",
    val activeLevel: String = "L0",
    val activeEngines: List<String> = emptyList(),
    val isPaused: Boolean = false,
    val isRunning: Boolean = false,
    val lastDecisionNote: String = ""
)

class AutonomousOrchestrator(
    private val context: Context,
    private val repository: MhvieRepository
) {
    private val barcodeProvider = ZXingBarcodeProvider()
    private val visionProvider = GeminiVisionIdentityProvider()
    private val openBeautyFacts = OpenBeautyFactsProvider()
    private val openverse = OpenverseImageProvider()
    private val wikimedia = WikimediaCommonsProvider()
    private val searxng = SearXNGSearchProvider()
    private val socialIndex = SocialPublicIndexProvider(searxng)
    private val downloader = SafeImageDownloader(context)
    private val verifier = GeminiVerificationAndScoringEngine()

    private val _progress = MutableStateFlow(OrchestratorProgress())
    val progress: StateFlow<OrchestratorProgress> = _progress.asStateFlow()

    @Volatile
    private var pauseRequested = false

    fun requestPause() {
        pauseRequested = true
        _progress.value = _progress.value.copy(isPaused = true, lastDecisionNote = "تم طلب الإيقاف المؤقت")
    }

    fun clearPause() {
        pauseRequested = false
        _progress.value = _progress.value.copy(isPaused = false)
    }

    suspend fun runBatch(
        uid: String,
        batch: BatchJob,
        products: List<ProductRecord>,
        engines: List<EngineConfig>,
        brands: List<BrandProfile>,
        settings: EngineSettings
    ) = withContext(Dispatchers.IO) {
        pauseRequested = false
        val enabledMap = engines.associateBy { it.engineKey }
        val searxEndpoint = enabledMap["searxng_meta"]?.endpointUrl?.ifBlank { settings.searxngBaseUrl }
            ?: settings.searxngBaseUrl

        val brandLookup = brands.associateBy { it.brandName.lowercase().trim() }.toMutableMap()
        val existingMemory = repository.getProductsOnce(uid)
            .filter { it.statusEnum() == ProductStatus.FOUND && it.visualSignatureHash.isNotBlank() }

        val targetProducts = products.filter {
            it.batchId == batch.id &&
                it.statusEnum() !in setOf(ProductStatus.FOUND, ProductStatus.ZERO_RESULT, ProductStatus.REVIEW_REQUIRED)
        }

        _progress.value = OrchestratorProgress(
            activeBatchId = batch.id,
            isRunning = true,
            lastDecisionNote = "بدء معالجة ${targetProducts.size} منتج باستراتيجية ${batch.strategyEnum().labelAr}"
        )

        repository.updateBatchProgress(
            batchId = batch.id,
            status = BatchStatus.RUNNING,
            processed = batch.processedProducts,
            found = batch.foundProductsCount,
            review = batch.reviewProductsCount,
            zero = batch.zeroResultCount,
            discoveredImages = batch.discoveredImagesCount
        )

        var processedCount = products.count {
            it.batchId == batch.id && it.statusEnum() in setOf(
                ProductStatus.FOUND, ProductStatus.REVIEW_REQUIRED, ProductStatus.ZERO_RESULT
            )
        }.toLong()
        var foundCount = products.count { it.batchId == batch.id && it.statusEnum() == ProductStatus.FOUND }.toLong()
        var reviewCount = products.count { it.batchId == batch.id && it.statusEnum() == ProductStatus.REVIEW_REQUIRED }.toLong()
        var zeroCount = products.count { it.batchId == batch.id && it.statusEnum() == ProductStatus.ZERO_RESULT }.toLong()
        var totalDiscovered = products.filter { it.batchId == batch.id }.sumOf { it.discoveredCount }

        val semaphore = Semaphore(settings.maxConcurrentTasks.coerceIn(1, 2))

        try {
            for (product in targetProducts) {
                currentCoroutineContext().ensureActive()
                if (pauseRequested) {
                    repository.updateBatchProgress(
                        batch.id, BatchStatus.PAUSED,
                        processedCount, foundCount, reviewCount, zeroCount, totalDiscovered
                    )
                    _progress.value = _progress.value.copy(isRunning = false, isPaused = true)
                    return@withContext
                }

                semaphore.withPermit {
                    val outcome = processSingleProduct(
                        uid = uid,
                        product = product,
                        strategy = batch.strategyEnum(),
                        targetImages = batch.targetImagesPerProduct.toInt(),
                        enabledMap = enabledMap,
                        searxEndpoint = searxEndpoint,
                        brandLookup = brandLookup,
                        visualMemory = existingMemory,
                        settings = settings
                    )
                    processedCount++
                    when (outcome.first) {
                        ProductStatus.FOUND -> foundCount++
                        ProductStatus.REVIEW_REQUIRED -> reviewCount++
                        ProductStatus.ZERO_RESULT -> zeroCount++
                        else -> Unit
                    }
                    totalDiscovered += outcome.second
                    repository.updateBatchProgress(
                        batchId = batch.id,
                        status = BatchStatus.RUNNING,
                        processed = processedCount,
                        found = foundCount,
                        review = reviewCount,
                        zero = zeroCount,
                        discoveredImages = totalDiscovered
                    )
                }
            }

            repository.updateBatchProgress(
                batchId = batch.id,
                status = BatchStatus.COMPLETED,
                processed = processedCount,
                found = foundCount,
                review = reviewCount,
                zero = zeroCount,
                discoveredImages = totalDiscovered
            )
            repository.appendLog("INFO", "Orchestrator", "اكتملت الدفعة ${batch.title}: ناجح=$foundCount، مراجعة=$reviewCount، صفر=$zeroCount")
        } catch (e: CancellationException) {
            repository.updateBatchProgress(
                batchId = batch.id,
                status = if (pauseRequested) BatchStatus.PAUSED else BatchStatus.CANCELLED,
                processed = processedCount,
                found = foundCount,
                review = reviewCount,
                zero = zeroCount,
                discoveredImages = totalDiscovered
            )
            throw e
        } catch (e: Exception) {
            Log.e(TAG, "Batch processing error", e)
            repository.appendLog("ERROR", "Orchestrator", "خطأ في الدفعة ${batch.title}: ${e.localizedMessage}")
            repository.updateBatchProgress(
                batchId = batch.id,
                status = BatchStatus.FAILED,
                processed = processedCount,
                found = foundCount,
                review = reviewCount,
                zero = zeroCount,
                discoveredImages = totalDiscovered
            )
        } finally {
            _progress.value = _progress.value.copy(isRunning = false)
        }
    }

    suspend fun reprocessSingleProduct(
        uid: String,
        product: ProductRecord,
        engines: List<EngineConfig>,
        brands: List<BrandProfile>,
        settings: EngineSettings
    ) = withContext(Dispatchers.IO) {
        val enabledMap = engines.associateBy { it.engineKey }
        val searxEndpoint = enabledMap["searxng_meta"]?.endpointUrl?.ifBlank { settings.searxngBaseUrl }
            ?: settings.searxngBaseUrl
        val brandLookup = brands.associateBy { it.brandName.lowercase().trim() }.toMutableMap()
        val memory = repository.getProductsOnce(uid)
            .filter { it.id != product.id && it.statusEnum() == ProductStatus.FOUND && it.visualSignatureHash.isNotBlank() }

        _progress.value = OrchestratorProgress(
            activeBatchId = product.batchId,
            activeProductTitle = product.displayTitle(),
            isRunning = true,
            lastDecisionNote = "إعادة البحث الذكي للمنتج"
        )
        try {
            processSingleProduct(
                uid = uid,
                product = product,
                strategy = SearchStrategy.DEEP_SOCIAL,
                targetImages = settings.defaultTargetImages,
                enabledMap = enabledMap,
                searxEndpoint = searxEndpoint,
                brandLookup = brandLookup,
                visualMemory = memory,
                settings = settings,
                bypassMemoryCache = true
            )
        } finally {
            _progress.value = _progress.value.copy(isRunning = false)
        }
    }

    private suspend fun processSingleProduct(
        uid: String,
        product: ProductRecord,
        strategy: SearchStrategy,
        targetImages: Int,
        enabledMap: Map<String, EngineConfig>,
        searxEndpoint: String,
        brandLookup: MutableMap<String, BrandProfile>,
        visualMemory: List<ProductRecord>,
        settings: EngineSettings,
        bypassMemoryCache: Boolean = false
    ): Pair<ProductStatus, Long> {
        val bitmaps = product.localOriginalPaths.mapNotNull {
            SecurityAndImageUtils.decodeScaledBitmapFromFile(it, 1024)
        }
        if (bitmaps.isEmpty()) {
            repository.updateProduct(
                product.id,
                mapOf(
                    "status" to ProductStatus.ZERO_RESULT.name,
                    "zeroResultReason" to ZeroResultReason.UNCERTAIN_IDENTITY.name,
                    "orchestratorNotes" to "تعذر قراءة ملف الصورة الأصلية من التخزين الداخلي"
                )
            )
            return ProductStatus.ZERO_RESULT to 0L
        }

        val primaryBitmap = bitmaps.first()
        val sigHash = SecurityAndImageUtils.computeDHash(primaryBitmap)

        // L0: Local Visual Memory Check
        _progress.value = _progress.value.copy(
            activeProductTitle = product.displayTitle(),
            activeLevel = "L0 — الذاكرة البصرية",
            activeEngines = listOf("VisualMemory")
        )
        if (!bypassMemoryCache) {
            val matchedMemory = visualMemory.firstOrNull { mem ->
                (product.barcode.isNotBlank() && mem.barcode == product.barcode) ||
                    SecurityAndImageUtils.hammingDistance(sigHash, mem.visualSignatureHash) <= 5
            }
            if (matchedMemory != null && matchedMemory.bestImageUrl.isNotBlank()) {
                val cachedCandidates = repository.getCandidatesOnce(uid, matchedMemory.id)
                    .filter { it.reviewDecision != ReviewDecision.REJECTED.name }
                    .take(targetImages)
                if (cachedCandidates.isNotEmpty()) {
                    cachedCandidates.forEach { cand ->
                        repository.saveCandidate(product.id, cand.copy(id = "", productId = product.id))
                    }
                    repository.updateProduct(
                        product.id,
                        mapOf(
                            "brand" to matchedMemory.brand,
                            "productNameEn" to matchedMemory.productNameEn,
                            "productNameAr" to matchedMemory.productNameAr,
                            "sizeWeight" to matchedMemory.sizeWeight,
                            "shadeColor" to matchedMemory.shadeColor,
                            "barcode" to matchedMemory.barcode,
                            "identityConfidence" to matchedMemory.identityConfidence,
                            "visualSignatureHash" to sigHash,
                            "status" to ProductStatus.FOUND.name,
                            "zeroResultReason" to ZeroResultReason.NONE.name,
                            "escalationLevelReached" to "L0",
                            "discoveredCount" to cachedCandidates.size.toLong(),
                            "matchedCount" to cachedCandidates.size.toLong(),
                            "bestImageUrl" to matchedMemory.bestImageUrl,
                            "orchestratorNotes" to "تم استرجاع الهوية والصور من الذاكرة البصرية التراكمية (L0)"
                        )
                    )
                    bitmaps.forEach { it.recycle() }
                    return ProductStatus.FOUND to cachedCandidates.size.toLong()
                }
            }
        }

        // L0.5: Barcode (ZXing) + Multimodal Identity Recognition (Gemini 3.8 Flash)
        repository.updateProduct(product.id, mapOf("status" to ProductStatus.IDENTIFYING.name))
        _progress.value = _progress.value.copy(
            activeLevel = "L0.5 — تحليل الهوية والباركود",
            activeEngines = listOf("ZXing", "Gemini 3.8 Flash")
        )

        val zxingBarcode = if (enabledMap["zxing_barcode"]?.enabled != false) {
            barcodeProvider.decodeBarcode(bitmaps)
        } else ""

        val hintBarcode = product.barcode.ifBlank { zxingBarcode }
        val hintText = listOf(product.skuCode, product.brand, product.productNameEn, product.sizeWeight, product.shadeColor)
            .filter { it.isNotBlank() }.joinToString(" ")

        val identityRes = if (enabledMap["gemini_vision"]?.enabled != false) {
            visionProvider.identifyProduct(bitmaps, hintBarcode, hintText)
        } else {
            Result.failure(IllegalStateException("محرك الرؤية معطّل"))
        }

        val identity = identityRes.getOrNull()
        val updatedProduct = product.copy(
            brand = identity?.brand?.ifBlank { product.brand } ?: product.brand,
            productNameEn = identity?.productNameEn?.ifBlank { product.productNameEn } ?: product.productNameEn,
            productNameAr = identity?.productNameAr?.ifBlank { product.productNameAr } ?: product.productNameAr,
            manufacturer = identity?.manufacturer ?: product.manufacturer,
            category = identity?.category ?: product.category,
            variantEdition = identity?.variantEdition ?: product.variantEdition,
            sizeWeight = identity?.sizeWeight?.ifBlank { product.sizeWeight } ?: product.sizeWeight,
            shadeColor = identity?.shadeColor?.ifBlank { product.shadeColor } ?: product.shadeColor,
            packagingType = identity?.packagingType ?: product.packagingType,
            barcode = identity?.visibleBarcode?.ifBlank { hintBarcode } ?: hintBarcode,
            extractedTextSummary = identity?.extractedTextSummary ?: "",
            identityConfidence = identity?.confidence ?: if (hintBarcode.isNotBlank()) 0.7 else 0.25,
            visualSignatureHash = sigHash,
            searchQueries = buildSmartQueries(identity, product, hintBarcode, brandLookup)
        )

        repository.updateProduct(
            product.id,
            mapOf(
                "brand" to updatedProduct.brand,
                "productNameEn" to updatedProduct.productNameEn,
                "productNameAr" to updatedProduct.productNameAr,
                "manufacturer" to updatedProduct.manufacturer,
                "category" to updatedProduct.category,
                "variantEdition" to updatedProduct.variantEdition,
                "sizeWeight" to updatedProduct.sizeWeight,
                "shadeColor" to updatedProduct.shadeColor,
                "packagingType" to updatedProduct.packagingType,
                "barcode" to updatedProduct.barcode,
                "extractedTextSummary" to updatedProduct.extractedTextSummary,
                "identityConfidence" to updatedProduct.identityConfidence,
                "visualSignatureHash" to sigHash,
                "searchQueries" to updatedProduct.searchQueries,
                "status" to ProductStatus.SEARCHING.name
            )
        )

        if (updatedProduct.identityConfidence < 0.30 && updatedProduct.searchQueries.isEmpty()) {
            repository.updateProduct(
                product.id,
                mapOf(
                    "status" to ProductStatus.ZERO_RESULT.name,
                    "zeroResultReason" to ZeroResultReason.UNCERTAIN_IDENTITY.name,
                    "escalationLevelReached" to "L1",
                    "orchestratorNotes" to "الصورة غير واضحة بما يكفي لتحديد الماركة أو الاسم أو الباركود دون تخمين"
                )
            )
            bitmaps.forEach { it.recycle() }
            return ProductStatus.ZERO_RESULT to 0L
        }

        // Adaptive Search Escalation L1 -> L5
        val rawHits = mutableListOf<CandidateSearchHit>()
        val engineErrors = mutableListOf<String>()
        var levelReached = "L1"
        val primaryQuery = updatedProduct.searchQueries.firstOrNull().orEmpty()

        // L1: Open Beauty Facts (Barcode + Name)
        if (enabledMap["open_beauty_facts"]?.enabled != false) {
            _progress.value = _progress.value.copy(
                activeProductTitle = updatedProduct.displayTitle(),
                activeLevel = "L1 — البحث بالباركود والاسم",
                activeEngines = listOf("Open Beauty Facts")
            )
            openBeautyFacts.search(updatedProduct, primaryQuery).fold(
                onSuccess = { rawHits.addAll(it) },
                onFailure = { engineErrors.add("OpenBeautyFacts: ${it.localizedMessage}") }
            )
        }

        // L2: Official Brand Knowledge Base & Open Licensed Media (Openverse + Wikimedia)
        if (rawHits.size < targetImages * 2) {
            levelReached = "L2"
            _progress.value = _progress.value.copy(
                activeLevel = "L2 — المصادر المرخصة والمواقع الرسمية",
                activeEngines = listOf("Openverse", "Wikimedia Commons")
            )
            val l2Query = updatedProduct.searchQueries.getOrElse(1) { primaryQuery }
            if (enabledMap["openverse_cc"]?.enabled != false) {
                openverse.search(updatedProduct, l2Query).fold(
                    onSuccess = { rawHits.addAll(it) },
                    onFailure = { engineErrors.add("Openverse: ${it.localizedMessage}") }
                )
            }
            if (enabledMap["wikimedia_commons"]?.enabled != false) {
                wikimedia.search(updatedProduct, primaryQuery).fold(
                    onSuccess = { rawHits.addAll(it) },
                    onFailure = { engineErrors.add("Wikimedia: ${it.localizedMessage}") }
                )
            }
        }

        // L3: Social Discovery & SearXNG Meta-Search (if enabled / configured)
        if ((strategy == SearchStrategy.DEEP_SOCIAL || rawHits.size < targetImages) &&
            settings.enableSocialDiscovery &&
            searxEndpoint.isNotBlank()
        ) {
            levelReached = "L3"
            _progress.value = _progress.value.copy(
                activeLevel = "L3 — البحث الموسع والاجتماعي (SearXNG)",
                activeEngines = listOf("SearXNG", "Instagram/Pinterest Index")
            )
            if (enabledMap["searxng_meta"]?.enabled != false) {
                searxng.search(updatedProduct, "$primaryQuery official product photography", searxEndpoint).fold(
                    onSuccess = { rawHits.addAll(it) },
                    onFailure = { engineErrors.add("SearXNG: ${it.localizedMessage}") }
                )
            }
            if (enabledMap["social_index"]?.enabled != false) {
                socialIndex.search(updatedProduct, primaryQuery, searxEndpoint).fold(
                    onSuccess = { rawHits.addAll(it) },
                    onFailure = { engineErrors.add("SocialIndex: ${it.localizedMessage}") }
                )
            }
        }

        // L4: Multi-Query Marketing Escalation if still sparse
        if (rawHits.size < targetImages && updatedProduct.searchQueries.size > 2) {
            levelReached = "L4"
            val extraQuery = updatedProduct.searchQueries[2]
            if (enabledMap["open_beauty_facts"]?.enabled != false) {
                openBeautyFacts.search(updatedProduct, extraQuery).onSuccess { rawHits.addAll(it) }
            }
            if (enabledMap["openverse_cc"]?.enabled != false) {
                openverse.search(updatedProduct, extraQuery).onSuccess { rawHits.addAll(it) }
            }
        }

        val uniqueHits = rawHits.distinctBy { it.imageUrl }.take(12)
        if (uniqueHits.isEmpty()) {
            val zeroReason = if (engineErrors.size >= 2) {
                ZeroResultReason.SOURCE_UNREACHABLE
            } else {
                ZeroResultReason.NO_MATCHING_IMAGES
            }
            repository.updateProduct(
                product.id,
                mapOf(
                    "status" to ProductStatus.ZERO_RESULT.name,
                    "zeroResultReason" to zeroReason.name,
                    "escalationLevelReached" to levelReached,
                    "orchestratorNotes" to if (engineErrors.isNotEmpty()) {
                        "أخطاء المحركات: ${engineErrors.joinToString(" | ")}"
                    } else {
                        "لم يتم العثور على نتائج في المصادر المفتوحة المتاحة (فعّل SearXNG لتوسيع البحث عبر الويب وInstagram)"
                    }
                )
            )
            bitmaps.forEach { it.recycle() }
            return ProductStatus.ZERO_RESULT to 0L
        }

        // L5: Download, Perceptual Deduplication (dHash), Identity Verification & Aesthetic Scoring
        levelReached = "L5"
        repository.updateProduct(product.id, mapOf("status" to ProductStatus.VERIFYING.name))
        _progress.value = _progress.value.copy(
            activeLevel = "L5 — التحقق من الهوية ومنع التكرار",
            activeEngines = listOf("SafeDownloader", "dHash", "Gemini Verification")
        )

        val seenHashes = mutableListOf<String>()
        var savedCount = 0L
        var matchedCount = 0L
        var lowQualityOnlyCount = 0
        var bestCandidateUrl = ""
        var bestCandidateScore = -1.0

        for (hit in uniqueHits) {
            currentCoroutineContext().ensureActive()
            val dl = downloader.downloadAndValidate(hit.imageUrl, product.id, saveLocally = false).getOrNull()
            if (dl != null) {
                // Deduplication check
                val isDuplicate = seenHashes.any { SecurityAndImageUtils.hammingDistance(it, dl.dHash) <= 5 }
                if (isDuplicate) {
                    dl.bitmap.recycle()
                    continue
                }
                seenHashes.add(dl.dHash)
            }

            val verdict = verifier.verifyCandidate(primaryBitmap, dl?.bitmap, updatedProduct, hit)
            dl?.bitmap?.recycle()

            if (verdict.imageCategory == ImageCategory.G_MISMATCH) {
                // Still record rejected mismatch for audit transparency or skip storing noisy mismatches
                if (verdict.matchScore >= 0.40) {
                    val rejectedCand = DiscoveredImage(
                        productId = product.id,
                        imageUrl = hit.imageUrl,
                        pageUrl = hit.pageUrl,
                        sourceName = hit.sourceName,
                        publisherName = hit.publisherName,
                        sourceType = hit.sourceType.name,
                        imageCategory = ImageCategory.G_MISMATCH.name,
                        rightsStatus = hit.rightsStatus.name,
                        licenseName = hit.licenseName,
                        matchScore = verdict.matchScore,
                        brandMatchScore = verdict.brandMatchScore,
                        skuMatchScore = verdict.skuMatchScore,
                        aestheticScore = verdict.aestheticScore,
                        widthPx = (dl?.widthPx ?: hit.widthPx).toLong(),
                        heightPx = (dl?.heightPx ?: hit.heightPx).toLong(),
                        perceptualHash = dl?.dHash.orEmpty(),
                        verificationNotes = verdict.notes,
                        reviewDecision = ReviewDecision.REJECTED.name,
                        rejectionReason = "عدم تطابق هوية المنتج (SKU/Size/Shade)"
                    )
                    repository.saveCandidate(product.id, rejectedCand)
                    savedCount++
                }
                continue
            }

            if (verdict.aestheticScore < settings.minAestheticScore && verdict.isMatch) {
                lowQualityOnlyCount++
            }

            val passesMatch = verdict.isMatch && verdict.matchScore >= settings.minMatchScore
            if (passesMatch) matchedCount++

            val compositeRank = verdict.matchScore * 0.65 + verdict.aestheticScore * 0.35
            if (passesMatch && compositeRank > bestCandidateScore) {
                bestCandidateScore = compositeRank
                bestCandidateUrl = hit.imageUrl
            }

            val cand = DiscoveredImage(
                productId = product.id,
                imageUrl = hit.imageUrl,
                pageUrl = hit.pageUrl,
                sourceName = hit.sourceName,
                publisherName = hit.publisherName,
                sourceType = hit.sourceType.name,
                imageCategory = verdict.imageCategory.name,
                rightsStatus = hit.rightsStatus.name,
                licenseName = hit.licenseName,
                matchScore = verdict.matchScore,
                brandMatchScore = verdict.brandMatchScore,
                skuMatchScore = verdict.skuMatchScore,
                aestheticScore = verdict.aestheticScore,
                widthPx = (dl?.widthPx ?: hit.widthPx).toLong(),
                heightPx = (dl?.heightPx ?: hit.heightPx).toLong(),
                perceptualHash = dl?.dHash.orEmpty(),
                verificationNotes = verdict.notes,
                reviewDecision = ReviewDecision.PENDING.name
            )
            repository.saveCandidate(product.id, cand)
            savedCount++

            if (settings.autoStopOnSufficientImages && matchedCount >= targetImages) {
                break
            }
        }

        // L7: Final Status Classification
        val finalStatus: ProductStatus
        val zeroReason: ZeroResultReason
        val notes: String

        when {
            matchedCount > 0 -> {
                finalStatus = ProductStatus.FOUND
                zeroReason = ZeroResultReason.NONE
                notes = "تم العثور على $matchedCount صور مطابقة من أصل $savedCount مرشح (المستوى $levelReached)"
            }
            savedCount > 0 -> {
                finalStatus = ProductStatus.REVIEW_REQUIRED
                zeroReason = ZeroResultReason.NONE
                notes = "تم حفظ $savedCount صور محتملة تحتاج مراجعة بشرية قبل الاعتماد"
            }
            lowQualityOnlyCount > 0 -> {
                finalStatus = ProductStatus.ZERO_RESULT
                zeroReason = ZeroResultReason.LOW_QUALITY_ONLY
                notes = "جميع الصور المكتشفة منخفضة الجودة أو تحتوي علامات مائية"
            }
            else -> {
                finalStatus = ProductStatus.ZERO_RESULT
                zeroReason = ZeroResultReason.NO_MATCHING_IMAGES
                notes = "لم تطابق أي من النتائج المسترجعة هوية المنتج بدقة (المستوى $levelReached)"
            }
        }

        repository.updateProduct(
            product.id,
            mapOf(
                "status" to finalStatus.name,
                "zeroResultReason" to zeroReason.name,
                "escalationLevelReached" to levelReached,
                "discoveredCount" to savedCount,
                "matchedCount" to matchedCount,
                "bestImageUrl" to bestCandidateUrl,
                "orchestratorNotes" to notes
            )
        )

        // Update Brand Knowledge Base memory
        if (updatedProduct.brand.isNotBlank()) {
            val key = updatedProduct.brand.lowercase().trim()
            val existingBrand = brandLookup[key]
            val newProcessed = (existingBrand?.processedCount ?: 0L) + 1L
            val prevSuccesses = ((existingBrand?.successRate ?: 0.0) * (existingBrand?.processedCount ?: 0L))
            val newSuccessRate = (prevSuccesses + if (finalStatus == ProductStatus.FOUND) 1.0 else 0.0) / newProcessed.toDouble()
            val updatedBrand = (existingBrand ?: BrandProfile(brandName = updatedProduct.brand)).copy(
                brandName = updatedProduct.brand,
                successfulQueries = ((existingBrand?.successfulQueries ?: emptyList()) + updatedProduct.searchQueries.take(2)).distinct().take(15),
                processedCount = newProcessed,
                successRate = newSuccessRate
            )
            brandLookup[key] = updatedBrand
            repository.upsertBrand(updatedBrand)
        }

        bitmaps.forEach { it.recycle() }
        return finalStatus to savedCount
    }

    private fun buildSmartQueries(
        identity: ProductIdentityExtraction?,
        product: ProductRecord,
        barcode: String,
        brandLookup: Map<String, BrandProfile>
    ): List<String> {
        val brand = identity?.brand?.ifBlank { product.brand } ?: product.brand
        val nameEn = identity?.productNameEn?.ifBlank { product.productNameEn } ?: product.productNameEn
        val variant = identity?.variantEdition ?: product.variantEdition
        val size = identity?.sizeWeight?.ifBlank { product.sizeWeight } ?: product.sizeWeight
        val shade = identity?.shadeColor?.ifBlank { product.shadeColor } ?: product.shadeColor

        val queries = mutableListOf<String>()
        val core = listOf(brand, nameEn, variant, size, shade).filter { it.isNotBlank() }.joinToString(" ")
        if (core.isNotBlank()) queries.add(core)

        val shortCore = listOf(brand, nameEn).filter { it.isNotBlank() }.joinToString(" ")
        if (shortCore.isNotBlank()) {
            queries.add(shortCore)
            queries.add("$shortCore product photography")
            queries.add("$shortCore official product campaign")
        }
        if (barcode.isNotBlank()) queries.add(barcode)
        identity?.searchQueries?.let { queries.addAll(it) }

        val brandProfile = brandLookup[brand.lowercase().trim()]
        if (brandProfile != null && brandProfile.officialWebsite.isNotBlank() && shortCore.isNotBlank()) {
            val domain = brandProfile.officialWebsite.removePrefix("https://").removePrefix("http://").substringBefore('/')
            if (domain.isNotBlank()) {
                queries.add("site:$domain $shortCore")
            }
        }
        return queries.map { it.trim() }.filter { it.isNotBlank() }.distinct().take(10)
    }

    private companion object {
        const val TAG = "AutonomousOrchestrator"
    }
}
