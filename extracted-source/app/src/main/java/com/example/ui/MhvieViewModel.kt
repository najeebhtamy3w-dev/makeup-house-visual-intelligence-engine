package com.example.ui

import android.app.Application
import android.graphics.Bitmap
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.CreationExtras
import androidx.lifecycle.viewModelScope
import com.example.core.EngineSettings
import com.example.core.SecurityAndImageUtils
import com.example.core.SettingsDataStore
import com.example.data.BackendGateway
import com.example.data.LocalWorkspace
import com.example.data.RemoteLink
import com.example.engine.OrchestratorProgress
import com.example.engine.ZXingBarcodeProvider
import com.example.export.BatchExporter
import com.example.model.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.util.UUID

sealed interface StudioUiState {
    data object Idle : StudioUiState
    data class Working(val message: String) : StudioUiState
    data class Ready(val path: String, val evidence: String) : StudioUiState
    data class Error(val message: String) : StudioUiState
}

/** Restores the recovered application's missing presentation state against the current service. */
class MhvieViewModel(application: Application, private val currentUserId: String) : AndroidViewModel(application) {
    private val workspace = LocalWorkspace(application)
    private val gateway = BackendGateway(application)
    private val preferences = SettingsDataStore(application)
    private val _batchesState = MutableStateFlow<UiState<List<BatchJob>>>(UiState.Loading)
    val batchesState = _batchesState.asStateFlow()
    private val _productsState = MutableStateFlow<UiState<List<ProductRecord>>>(UiState.Loading)
    val productsState = _productsState.asStateFlow()
    private val _brandsState = MutableStateFlow<UiState<List<BrandProfile>>>(UiState.Loading)
    val brandsState = _brandsState.asStateFlow()
    private val _enginesState = MutableStateFlow<UiState<List<EngineConfig>>>(UiState.Loading)
    val enginesState = _enginesState.asStateFlow()
    private val _logsState = MutableStateFlow<UiState<List<EngineAuditLog>>>(UiState.Loading)
    val logsState = _logsState.asStateFlow()
    private val _selectedCandidatesState = MutableStateFlow<UiState<List<DiscoveredImage>>>(UiState.Success(emptyList()))
    val selectedCandidatesState = _selectedCandidatesState.asStateFlow()
    private val _selectedBatchId = MutableStateFlow<String?>(null)
    val selectedBatchId = _selectedBatchId.asStateFlow()
    private var selectedProductId: String? = null
    private val _orchestratorProgress = MutableStateFlow(OrchestratorProgress())
    val orchestratorProgress = _orchestratorProgress.asStateFlow()
    val settings = preferences.settingsFlow.stateIn(viewModelScope, SharingStarted.Eagerly, EngineSettings())
    private val _studioState = MutableStateFlow<StudioUiState>(StudioUiState.Idle)
    val studioState = _studioState.asStateFlow()
    private val _isBenchmarking = MutableStateFlow(false)
    val isBenchmarking = _isBenchmarking.asStateFlow()
    private val _snackbarMessage = MutableStateFlow<String?>(null)
    val snackbarMessage = _snackbarMessage.asStateFlow()
    val backendEndpoint = MutableStateFlow(gateway.endpoint)
    private var processing: Job? = null
    @Volatile private var pauseRequested = false
    @Volatile private var cancelRequested = false
    private val studioResults = java.util.concurrent.ConcurrentHashMap<String, StudioUiState>()

    init {
        io {
            workspace.batches().filter { it.statusEnum() == BatchStatus.RUNNING }.forEach { workspace.save(it.copy(status = BatchStatus.PAUSED.name)) }
            if (workspace.engines().isEmpty()) {
                workspace.save(EngineConfig(id = "mhvie_backend", engineKey = "mhvie_backend", displayName = "MH-VIE — محركك الخارجي", category = "BACKEND", costTier = "OWNER_HOSTED", endpointUrl = gateway.endpoint, lastHealthStatus = "NOT_TESTED", lastTestSummary = "الاتصال لا يثبت جاهزية النماذج؛ شغّل فحصًا فعليًا"))
                workspace.save(EngineConfig(id = "zxing_barcode", engineKey = "zxing_barcode", displayName = "ZXing — قراءة الباركود على الهاتف", category = "BARCODE", costTier = "FREE_LOCAL", lastHealthStatus = "NOT_TESTED"))
            }
            refresh()
        }
    }
    private fun app(): Application = getApplication()
    private fun io(block: suspend () -> Unit): Job = viewModelScope.launch(Dispatchers.IO) {
        try { block() } catch (e: CancellationException) { throw e } catch (e: Exception) { _snackbarMessage.value = e.message?.take(240) ?: "تعذر إكمال العملية" }
    }
    private fun refresh() {
        _batchesState.value = UiState.Success(workspace.batches())
        _productsState.value = UiState.Success(workspace.products())
        _brandsState.value = UiState.Success(workspace.brands())
        _enginesState.value = UiState.Success(workspace.engines().sortedBy { it.priorityOrder })
        _logsState.value = UiState.Success(workspace.logs())
        _selectedCandidatesState.value = UiState.Success(workspace.candidates().filter { it.productId == selectedProductId })
    }
    private fun log(level: String, message: String) { workspace.save(EngineAuditLog(id = UUID.randomUUID().toString(), level = level, component = "MH-VIE", message = message.take(500))) }
    fun readBarcode(product: ProductRecord) { io {
        val bitmap = product.localOriginalPaths.firstOrNull()?.let { SecurityAndImageUtils.decodeScaledBitmapFromFile(it, 2400) } ?: error("الصورة الأصلية غير متاحة")
        val code = try { ZXingBarcodeProvider().decodeBarcode(listOf(bitmap)) } finally { bitmap.recycle() }
        require(code.isNotBlank()) { "لم يُقرأ باركود واضح؛ التقط صورة أقرب أو أدخله يدويًا" }
        workspace.save(product.copy(barcode = code, orchestratorNotes = "باركود مقروء من الصورة؛ يتطلب تحققًا قبل البحث")); refresh()
    } }
    fun shareStudio(path: String) { io {
        val file = File(path); val root = File(app().filesDir, "mhvie_images/studio").canonicalFile
        require(file.canonicalFile.parentFile == root && file.isFile)
        withContext(Dispatchers.Main) { BatchExporter.shareFile(app(), file, "image/png", "ناتج الاستوديو للمراجعة") }
    } }
    fun clearSnackbar() { _snackbarMessage.value = null }
    fun selectBatch(id: String) { _selectedBatchId.value = id }
    fun selectProduct(id: String) { selectedProductId = id; _studioState.value = studioResults[id] ?: StudioUiState.Idle; io {
        workspace.links().firstOrNull { it.productId == id + "#studio" && it.localOutputPath.isNotBlank() }?.let { link ->
            if (File(link.localOutputPath).isFile) setStudio(id, StudioUiState.Ready(link.localOutputPath, link.responseJson))
        }; refresh()
    } }
    private fun setStudio(productId: String, value: StudioUiState) { studioResults[productId] = value; if (selectedProductId == productId) _studioState.value = value }
    fun updateSettings(transform: (EngineSettings) -> EngineSettings) { io { preferences.updateSettings(transform) } }
    fun updateBackendConnection(endpoint: String, token: String) { io {
        gateway.saveConnection(endpoint, token)
        backendEndpoint.value = gateway.endpoint
        val current = workspace.engines().first { it.engineKey == "mhvie_backend" }
        workspace.save(current.copy(endpointUrl = gateway.endpoint, lastHealthStatus = "NOT_TESTED", lastTestSummary = "تم حفظ الاتصال مشفرًا على الجهاز"))
        refresh(); _snackbarMessage.value = "حُفظ اتصال المحرك. شغّل فحص الاتصال."
    } }
    fun upsertBrand(brand: BrandProfile) { io { require(brand.brandName.isNotBlank()); workspace.save(brand.copy(id = brand.id.ifBlank { UUID.randomUUID().toString() })); refresh() } }
    fun toggleEngine(engine: EngineConfig, enabled: Boolean) { io { workspace.save(engine.copy(enabled = enabled)); refresh() } }
    fun updateSearxngEndpoint(engine: EngineConfig, url: String) { io {
        require(url.startsWith("https://")) { "HTTPS مطلوب" }
        if (engine.engineKey == "mhvie_backend") { gateway.saveConnection(url, ""); backendEndpoint.value = gateway.endpoint }
        workspace.save(engine.copy(endpointUrl = url, lastHealthStatus = "NOT_TESTED")); refresh()
    } }
    fun runLiveEngineBenchmarks() { io {
        _isBenchmarking.value = true
        try {
            val start = System.nanoTime()
            val result = gateway.json("v1/health")
            val current = workspace.engines().first { it.engineKey == "mhvie_backend" }
            workspace.save(current.copy(lastHealthStatus = "API_AVAILABLE", lastLatencyMs = (System.nanoTime() - start) / 1_000_000, lastTestSummary = result.toString().take(500)))
            log("INFO", "نجح اتصال API. جاهزية النماذج: ${result.optString("model_readiness", "NOT_VERIFIED")}")
        } catch (e: Exception) {
            val current = workspace.engines().first { it.engineKey == "mhvie_backend" }
            workspace.save(current.copy(lastHealthStatus = "UNAVAILABLE", lastTestSummary = e.message.orEmpty().take(200)))
            _snackbarMessage.value = "تعذر اتصال المحرك: ${e.message}"
        } finally { _isBenchmarking.value = false; refresh() }
    } }

    fun createAndStartBatchFromPhotos(title: String, uris: List<Uri>, single: Boolean, csv: Uri?, strategy: SearchStrategy, target: Int, onCreated: () -> Unit) { io {
        require(uris.isNotEmpty()) { "اختر صورة واحدة على الأقل" }
        val id = UUID.randomUUID().toString()
        val paths = uris.map { SecurityAndImageUtils.copyUriToInternalImageFile(app(), it, id) ?: error("تعذر استيراد صورة؛ تحقق من نوعها وحجمها") }
        val groups = if (single) listOf(paths) else paths.map { listOf(it) }
        createBatch(id, title, groups, csv, strategy, target)
        withContext(Dispatchers.Main) { onCreated() }
        workspace.batches().firstOrNull { it.id == id }?.let { resumeBatch(it) }
    } }
    fun createAndStartBatchFromZip(title: String, zip: Uri, csv: Uri?, strategy: SearchStrategy, target: Int, onCreated: () -> Unit) { io {
        val id = UUID.randomUUID().toString()
        val groups = SecurityAndImageUtils.safeExtractImagesFromZip(app(), zip, id).getOrThrow()
        createBatch(id, title, groups.map { it.filePaths }, csv, strategy, target)
        withContext(Dispatchers.Main) { onCreated() }
        workspace.batches().firstOrNull { it.id == id }?.let { resumeBatch(it) }
    } }
    private fun createBatch(id: String, title: String, groups: List<List<String>>, csv: Uri?, strategy: SearchStrategy, target: Int) {
        val hints = csv?.let { SecurityAndImageUtils.parseCsvProductHints(app(), it) }.orEmpty()
        workspace.transaction {
            workspace.save(BatchJob(id = id, userId = currentUserId, title = title.trim().ifBlank { "دفعة ${workspace.batches().size + 1}" }, totalProducts = groups.size.toLong(), strategy = strategy.name, targetImagesPerProduct = target.toLong()))
            groups.forEachIndexed { index, paths ->
                val hint = hints.getOrNull(index)
                workspace.save(ProductRecord(id = UUID.randomUUID().toString(), userId = currentUserId, batchId = id, localOriginalPaths = paths, skuCode = hint?.sku.orEmpty(), brand = hint?.brand.orEmpty(), productNameEn = hint?.name.orEmpty(), sizeWeight = hint?.size.orEmpty(), shadeColor = hint?.shade.orEmpty(), barcode = hint?.barcode.orEmpty(), orchestratorNotes = "أصل محفوظ محليًا؛ بيانات CSV إن وجدت إدخال بشري يحتاج مراجعة"))
            }
        }
        selectBatch(id); refresh()
    }
    fun saveManualIdentity(product: ProductRecord) { io {
        val prior = workspace.products().firstOrNull { it.id == product.id } ?: return@io
        workspace.save(prior.copy(brand = product.brand.trim(), productNameEn = product.productNameEn.trim(), productNameAr = product.productNameAr.trim(), sizeWeight = product.sizeWeight.trim(), barcode = product.barcode.trim(), variantEdition = product.variantEdition.trim(), shadeColor = product.shadeColor.trim(), orchestratorNotes = "تصحيح بشري محفوظ؛ ليس اعتمادًا آليًا للهوية أو الحقوق")); refresh()
    } }
    fun pauseBatch() { pauseRequested = true; _snackbarMessage.value = "أُوقفت متابعة الدفعة؛ قد تستمر مهمة الخادم المرسلة بالفعل. استخدم إلغاء لإيقافها." }
    fun cancelBatch(batch: BatchJob) { io {
        pauseRequested = true; cancelRequested = true
        workspace.links().filter { it.batchId == batch.id && it.state in setOf("QUEUED", "RUNNING") }.forEach { link -> gateway.json("v1/batches/${link.remoteBatchId}/cancel", "POST"); workspace.save(link.copy(state = "CANCELLED")) }
        workspace.save(batch.copy(status = BatchStatus.CANCELLED.name)); refresh()
    } }
    fun resumeBatch(batch: BatchJob) {
        if (processing?.isActive == true) { _snackbarMessage.value = "توجد دفعة قيد المتابعة؛ أوقفها قبل تشغيل دفعة أخرى"; return }
        pauseRequested = false; cancelRequested = false
        processing = io { processBatch(batch.id) }
    }
    private suspend fun processBatch(batchId: String) {
        var batch = workspace.batches().first { it.id == batchId }
        if (!gateway.configured() || workspace.engines().firstOrNull { it.engineKey == "mhvie_backend" }?.enabled != true) {
            workspace.save(batch.copy(status = BatchStatus.PAUSED.name)); refresh(); _snackbarMessage.value = "الدفعة محفوظة. اضبط خادم MH-VIE ورمز الوصول ثم استأنف."; return
        }
        workspace.save(batch.copy(status = BatchStatus.RUNNING.name)); refresh()
        _orchestratorProgress.value = OrchestratorProgress(activeBatchId = batch.id, isRunning = true, activeLevel = "BACKEND", activeEngines = listOf("MH-VIE"))
        try {
            for (product in workspace.products().filter { it.batchId == batchId && it.statusEnum() !in setOf(ProductStatus.FOUND, ProductStatus.REVIEW_REQUIRED, ProductStatus.ZERO_RESULT) }.reversed()) {
                if (pauseRequested) break
                _orchestratorProgress.value = _orchestratorProgress.value.copy(activeProductTitle = product.displayTitle())
                try {
                    var link = workspace.links().firstOrNull { it.productId == product.id }
                    if (link == null || link.state in setOf("COMPLETED", "FAILED", "CANCELLED", "REQUEST_NEW")) {
                        val original = product.localOriginalPaths.firstOrNull()?.let(::File) ?: error("الصورة الأصلية مفقودة")
                        val input = gateway.upload(original)
                        val query = listOf(product.brand, product.productNameEn.ifBlank { product.productNameAr }, product.sizeWeight, product.shadeColor).filter { it.isNotBlank() }.joinToString(" ").take(240)
                        val kind = when { product.barcode.isNotBlank() -> "smart_discover"; product.productNameEn.isNotBlank() || product.productNameAr.isNotBlank() -> "discover"; else -> "photo_discover" }
                        val payload = JSONObject().put("kind", kind).put("purpose", "catalog").put("input", input)
                        if (query.isNotBlank()) payload.put("query", query)
                        if (product.barcode.isNotBlank()) payload.put("barcode", product.barcode)
                        val generation = link?.generation ?: 0
                        val key = product.id + "-" + sha(payload.toString().toByteArray()).take(20) + "-" + generation
                        val submitted = gateway.json("v1/batches", "POST", JSONObject().put("jobs", JSONArray().put(payload)), key)
                        val remoteId = submitted.getString("batch_id"); require(remoteId.matches(Regex("[a-f0-9]{32}"))) { "INVALID_BATCH_ID" }
                        link = RemoteLink(product.id, batchId, input, kind, remoteId, generation = generation)
                        workspace.save(link)
                    }
                    workspace.save(product.copy(status = if (link.kind == "photo_discover") ProductStatus.IDENTIFYING.name else ProductStatus.SEARCHING.name, orchestratorNotes = "مهمة الخادم ${link.remoteBatchId}")); refresh()
                    val result = waitForRemote(link)
                    if (result != null) applyResult(product, result)
                } catch (e: CancellationException) { throw e } catch (e: Exception) {
                    workspace.save(product.copy(status = ProductStatus.FAILED.name, orchestratorNotes = e.message.orEmpty().take(500)))
                    log("ERROR", "المنتج ${product.id}: ${e.message.orEmpty().take(200)}")
                }
                recalculateBatch(batchId, BatchStatus.RUNNING); refresh()
            }
            recalculateBatch(batchId, if (cancelRequested) BatchStatus.CANCELLED else if (pauseRequested) BatchStatus.PAUSED else BatchStatus.COMPLETED)
        } finally {
            _orchestratorProgress.value = _orchestratorProgress.value.copy(isRunning = false, isPaused = pauseRequested)
            refresh()
        }
    }
    private suspend fun waitForRemote(link: RemoteLink): JSONObject? {
        while (currentCoroutineContext().isActive && !pauseRequested) {
            val response = gateway.json("v1/batches/${link.remoteBatchId}")
            val jobs = response.getJSONArray("jobs")
            val job = jobs.getJSONObject(0)
            val state = job.getString("state")
            workspace.save(link.copy(jobId = job.getString("id"), state = state, responseJson = response.toString()))
            _orchestratorProgress.value = _orchestratorProgress.value.copy(lastDecisionNote = "الخادم: $state")
            if (state == "COMPLETED") return job
            if (state in setOf("FAILED", "CANCELLED")) error(job.optString("error").takeUnless { it.isBlank() || it == "null" } ?: state)
            delay(1500)
        }
        return null
    }
    private fun applyResult(product: ProductRecord, job: JSONObject) {
        val result = job.optJSONObject("result") ?: error("نتيجة الخادم فارغة")
        val identity = result.optJSONObject("identity")?.optJSONObject("fields") ?: result.optJSONObject("fields")
        var updated = product
        if (identity != null) updated = product.copy(brand = identity.optString("brand", product.brand), productNameEn = identity.optString("name", product.productNameEn), sizeWeight = identity.optString("size", product.sizeWeight), variantEdition = identity.optString("variant", product.variantEdition), shadeColor = identity.optString("shade", product.shadeColor), extractedTextSummary = result.optJSONObject("identity")?.toString()?.take(2000).orEmpty())
        val candidates = result.optJSONArray("candidates") ?: JSONArray()
        for (i in 0 until candidates.length()) {
            val row = candidates.getJSONObject(i); val digest = row.optString("sha256")
            if (!digest.matches(Regex("[a-f0-9]{64}"))) continue
            val evidence = row.optJSONObject("identity_assessment")
            val rejected = row.optJSONObject("selection")?.optString("status") == "REJECTED" || evidence?.optString("status") == "CONFLICT"
            workspace.save(DiscoveredImage(id = product.id + "_" + digest, productId = product.id, imageUrl = row.optString("url"), pageUrl = row.optString("source"), sourceName = row.optString("discovery_stage", "خادم MH-VIE"), imageCategory = if (rejected) ImageCategory.G_MISMATCH.name else ImageCategory.H_REVIEW.name, rightsStatus = RightsStatus.RIGHTS_UNKNOWN.name, matchScore = 0.0, widthPx = row.optLong("width"), heightPx = row.optLong("height"), perceptualHash = digest, verificationNotes = row.toString().take(8000)))
        }
        workspace.save(updated.copy(status = if (candidates.length() > 0 || result.optString("status").contains("REVIEW")) ProductStatus.REVIEW_REQUIRED.name else ProductStatus.ZERO_RESULT.name, zeroResultReason = if (candidates.length() == 0) ZeroResultReason.NO_MATCHING_IMAGES.name else ZeroResultReason.NONE.name, discoveredCount = candidates.length().toLong(), matchedCount = 0, identityConfidence = 0.0, orchestratorNotes = "اكتملت المعالجة؛ الهوية والحقوق تحتاجان مراجعة بشرية.\n${result.optString("status")}", searchQueries = listOf(result.optString("query")).filter { it.isNotBlank() }))
    }
    private fun recalculateBatch(id: String, status: BatchStatus) {
        val batch = workspace.batches().first { it.id == id }; val products = workspace.products().filter { it.batchId == id }
        workspace.save(batch.copy(status = status.name, processedProducts = products.count { it.statusEnum() in setOf(ProductStatus.FAILED, ProductStatus.ZERO_RESULT, ProductStatus.REVIEW_REQUIRED, ProductStatus.FOUND) }.toLong(), reviewProductsCount = products.count { it.statusEnum() == ProductStatus.REVIEW_REQUIRED }.toLong(), foundProductsCount = products.count { it.statusEnum() == ProductStatus.FOUND }.toLong(), zeroResultCount = products.count { it.statusEnum() == ProductStatus.ZERO_RESULT }.toLong(), discoveredImagesCount = products.sumOf { it.discoveredCount }))
    }
    fun retryZeroOrFailedInBatch(batch: BatchJob) { io {
        workspace.products().filter { it.batchId == batch.id && it.statusEnum() in setOf(ProductStatus.FAILED, ProductStatus.ZERO_RESULT) }.forEach { p ->
            val link = workspace.links().firstOrNull { it.productId == p.id }
            if (link != null) {
                if (link.state == "COMPLETED") workspace.save(link.copy(state = "REQUEST_NEW", generation = link.generation + 1))
                else { gateway.json("v1/batches/${link.remoteBatchId}/retry", "POST"); workspace.save(link.copy(state = "QUEUED")) }
            }
            workspace.save(p.copy(status = ProductStatus.PENDING.name))
        }; refresh(); resumeBatch(batch)
    } }
    fun reprocessProduct(product: ProductRecord) { io {
        workspace.links().firstOrNull { it.productId == product.id }?.let { workspace.save(it.copy(state = "REQUEST_NEW", generation = it.generation + 1)) }
        workspace.save(product.copy(status = ProductStatus.PENDING.name)); refresh()
        workspace.batches().firstOrNull { it.id == product.batchId }?.let { resumeBatch(it) }
    } }
    fun approveCandidate(productId: String, candidate: DiscoveredImage) { io {
        require(candidate.localSavedPath.isNotBlank()) { "نزّل نسخة المراجعة أولًا" }
        require(candidate.categoryEnum() != ImageCategory.G_MISMATCH) { "الصورة مرفوضة الهوية؛ لا يمكن اعتمادها" }
        workspace.save(candidate.copy(reviewDecision = ReviewDecision.APPROVED.name, verificationNotes = candidate.verificationNotes + "\nاعتماد بشري لجودة الصورة؛ الحقوق لم تُعتمد"))
        val product = workspace.products().first { it.id == productId }
        workspace.save(product.copy(bestImageUrl = candidate.localSavedPath)); refresh()
    } }
    fun rejectCandidate(productId: String, candidateId: String) { io { workspace.candidates().firstOrNull { it.productId == productId && it.id == candidateId }?.let { workspace.save(it.copy(reviewDecision = ReviewDecision.REJECTED.name)) }; refresh() } }
    fun batchApproveProducts(ids: Set<String>) { io {
        ids.forEach { id -> workspace.products().firstOrNull { it.id == id }?.let { p -> workspace.save(p.copy(approvalStatus = ApprovalStatus.APPROVED.name, orchestratorNotes = p.orchestratorNotes + "\nاعتماد بشري للمنتج؛ لا يغيّر حقوق الصور")) } }; refresh()
    } }
    fun downloadCandidateLocally(productId: String, candidate: DiscoveredImage) { io {
        val link = workspace.links().firstOrNull { it.productId == productId } ?: error("مهمة الخادم مفقودة")
        require(link.jobId.matches(Regex("[a-f0-9]{32}")))
        val digest = candidate.perceptualHash; require(digest.matches(Regex("[a-f0-9]{64}")))
        val file = gateway.download("v1/batches/${link.remoteBatchId}/jobs/${link.jobId}/files/$digest.bin", File(app().filesDir, "mhvie_images/candidates/$digest.bin"), 10_000_000, expectedSha256 = digest)
        check(sha(file.readBytes()) == digest) { "فشل التحقق من بصمة الصورة" }
        workspace.save(candidate.copy(localSavedPath = file.absolutePath)); refresh(); _snackbarMessage.value = "حُفظت نسخة المراجعة وبصمتها مطابقة؛ الحقوق ما زالت غير معتمدة"
    } }
    fun generateCreativeStudioImage(product: ProductRecord, prompt: String) { io {
        require(processing?.isActive != true) { "أوقف متابعة دفعة البحث قبل تشغيل الاستوديو" }
        pauseRequested = false
        require(prompt.isNotBlank()) { "اكتب وصف التعديل المطلوب" }
        setStudio(product.id, StudioUiState.Working("رفع الأصل وإرسال أمر التحرير إلى محركك"))
        try {
            val original = File(product.localOriginalPaths.firstOrNull() ?: error("الأصل مفقود"))
            val input = gateway.upload(original)
            val brand = settings.value.brandProfile
            val payload = JSONObject().put("kind", "direct_edit").put("input", input).put("prompt", prompt.take(1500)).put("brand", brand).put("formats", JSONArray(listOf("square", "portrait", "story")))
            val response = gateway.json("v1/batches", "POST", JSONObject().put("jobs", JSONArray().put(payload)), "studio-${product.id}-${sha(payload.toString().toByteArray()).take(20)}")
            val link = RemoteLink(product.id + "#studio", product.batchId, input, "direct_edit", response.getString("batch_id")); workspace.save(link)
            val job = waitForRemote(link) ?: error("أُوقفت المتابعة؛ مهمة الاستوديو محفوظة على الخادم")
            val result = job.getJSONObject("result")
            val expected = result.optJSONObject("artifacts")?.optJSONObject("edited.png")?.optString("sha256")
            val file = gateway.download("v1/batches/${link.remoteBatchId}/jobs/${job.getString("id")}/files/edited.png", File(app().filesDir, "mhvie_images/studio/${job.getString("id")}.png"), expectedSha256 = expected)
            check(expected != null && sha(file.readBytes()) == expected) { "تعذر التحقق من بصمة ناتج الاستوديو" }
            workspace.links().firstOrNull { it.productId == link.productId }?.let { workspace.save(it.copy(localOutputPath = file.absolutePath)) }
            setStudio(product.id, StudioUiState.Ready(file.absolutePath, result.toString()))
        } catch (e: CancellationException) { throw e } catch (e: Exception) { setStudio(product.id, StudioUiState.Error(e.message.orEmpty())) }
    } }
    fun exportBatch(batch: BatchJob, format: ExportFormat) { io {
        val products = workspace.products().filter { it.batchId == batch.id }; val candidates = workspace.candidates().groupBy { it.productId }
        val file = when (format) {
            ExportFormat.ZIP -> BatchExporter.exportBatchZip(app(), batch, products, candidates)
            ExportFormat.CSV_EXCEL -> BatchExporter.exportCsvExcel(app(), batch, products, candidates)
            ExportFormat.HTML_GALLERY -> BatchExporter.exportHtmlGallery(app(), batch, products, candidates)
            ExportFormat.JSON -> BatchExporter.exportBatchJson(app(), batch, products, candidates)
        }
        withContext(Dispatchers.Main) { BatchExporter.shareFile(app(), file, when (format) { ExportFormat.ZIP -> "application/zip"; ExportFormat.JSON -> "application/json"; ExportFormat.HTML_GALLERY -> "text/html"; ExportFormat.CSV_EXCEL -> "text/csv" }, "تصدير MH-VIE") }
    } }
    fun exportKnowledgeBaseBackup() { io {
        val root = JSONObject().put("schema_version", 1)
        fun <T> array(values: List<T>, type: Class<T>) = JSONArray(values.map { JSONObject(workspace.json.adapter(type).toJson(it)) })
        root.put("products", array(workspace.products(), ProductRecord::class.java)); root.put("batches", array(workspace.batches(), BatchJob::class.java)); root.put("brands", array(workspace.brands(), BrandProfile::class.java)); root.put("candidates", array(workspace.candidates(), DiscoveredImage::class.java))
        val file = File(app().filesDir, "backups/MH_VIE_WORKSPACE.json").apply { parentFile?.mkdirs(); writeText(root.toString(2)) }
        withContext(Dispatchers.Main) { BatchExporter.shareFile(app(), file, "application/json", "نسخة بيانات MH-VIE — الصور عبر ZIP") }
    } }
    fun restoreKnowledgeBaseBackup(uri: Uri) { io {
        val bytes = app().contentResolver.openInputStream(uri)?.use { stream -> val buffer = java.io.ByteArrayOutputStream(); val chunk = ByteArray(8192); while (true) { val n = stream.read(chunk); if (n < 0) break; require(buffer.size() + n <= 20_000_000) { "النسخة تتجاوز 20MB" }; buffer.write(chunk,0,n) }; buffer.toByteArray() } ?: error("تعذر قراءة النسخة")
        val root = JSONObject(bytes.toString(Charsets.UTF_8)); require(root.optInt("schema_version") == 1) { "صيغة النسخة غير مدعومة" }
        require(workspace.products().isEmpty() && workspace.batches().isEmpty()) { "الاسترجاع متاح لمساحة فارغة لحماية البيانات القائمة" }
        workspace.transaction {
            fun <T> restore(key: String, type: Class<T>, save: (T) -> Unit) { val rows = root.optJSONArray(key) ?: return; require(rows.length() <= 10000); for (i in 0 until rows.length()) workspace.json.adapter(type).fromJson(rows.getJSONObject(i).toString())?.let(save) }
            restore("batches", BatchJob::class.java) { require(it.id.matches(Regex("[a-zA-Z0-9_-]{1,120}"))); workspace.save(it) }
            restore("products", ProductRecord::class.java) { p -> require(p.id.matches(Regex("[a-zA-Z0-9_-]{1,120}")) && p.batchId.matches(Regex("[a-zA-Z0-9_-]{1,120}"))); workspace.save(p.copy(localOriginalPaths = emptyList(), bestImageUrl = "", orchestratorNotes = p.orchestratorNotes + "\nاستُرجعت البيانات دون الصور؛ أعد استيراد الصور", status = ProductStatus.REVIEW_REQUIRED.name)) }
            restore("brands", BrandProfile::class.java) { workspace.save(it) }
            restore("candidates", DiscoveredImage::class.java) { workspace.save(it.copy(localSavedPath = "")) }
        }; refresh(); _snackbarMessage.value = "استُرجعت البيانات. الصور تُنقل بصورة مستقلة عبر ZIP."
    } }
    private fun sha(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
    companion object {
        fun provideFactory(uid: String): ViewModelProvider.Factory = object : ViewModelProvider.Factory {
            override fun <T : ViewModel> create(modelClass: Class<T>, extras: CreationExtras): T {
                val app = checkNotNull(extras[ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY])
                @Suppress("UNCHECKED_CAST") return MhvieViewModel(app, uid) as T
            }
        }
    }
}
