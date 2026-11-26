package com.example.data

import android.content.Context
import com.example.R
import com.example.model.ApprovalStatus
import com.example.model.BatchJob
import com.example.model.BatchStatus
import com.example.model.BrandProfile
import com.example.model.DiscoveredImage
import com.example.model.EngineAuditLog
import com.example.model.EngineConfig
import com.example.model.ProductRecord
import com.example.model.ReviewDecision
import com.google.firebase.Firebase
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.auth
import com.google.firebase.firestore.DocumentSnapshot
import com.google.firebase.firestore.FieldValue
import com.google.firebase.firestore.FirebaseFirestore
import com.google.firebase.firestore.snapshots
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emitAll
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.tasks.await
import java.util.UUID

class MhvieRepository(
    private val db: FirebaseFirestore,
    private val auth: FirebaseAuth = Firebase.auth
) {
    constructor(context: Context) : this(
        FirebaseFirestore.getInstance(
            context.applicationContext.getString(R.string.firestore_database_id)
        )
    )

    private fun requireUserId(): String =
        auth.currentUser?.uid
            ?: throw IllegalStateException("يجب تسجيل الدخول بحساب Google قبل الوصول إلى قاعدة البيانات.")

    private fun userDoc(uid: String) = db.collection("users").document(uid)

    fun observeBatches(uid: String): Flow<List<BatchJob>> = flow {
        require(uid.isNotBlank()) { "User ID must not be blank" }
        emitAll(
            userDoc(uid).collection("batches")
                .snapshots()
                .map { snap ->
                    snap.toObjects(BatchJob::class.java, DocumentSnapshot.ServerTimestampBehavior.ESTIMATE)
                        .sortedByDescending { it.createdAt?.seconds ?: 0L }
                }
        )
    }

    fun observeProducts(uid: String): Flow<List<ProductRecord>> = flow {
        require(uid.isNotBlank()) { "User ID must not be blank" }
        emitAll(
            userDoc(uid).collection("products")
                .snapshots()
                .map { snap ->
                    snap.toObjects(ProductRecord::class.java, DocumentSnapshot.ServerTimestampBehavior.ESTIMATE)
                        .sortedByDescending { it.updatedAt?.seconds ?: it.createdAt?.seconds ?: 0L }
                }
        )
    }

    fun observeCandidates(uid: String, productId: String): Flow<List<DiscoveredImage>> = flow {
        require(uid.isNotBlank() && productId.isNotBlank()) { "IDs must not be blank" }
        emitAll(
            userDoc(uid).collection("products").document(productId).collection("candidates")
                .snapshots()
                .map { snap ->
                    snap.toObjects(DiscoveredImage::class.java, DocumentSnapshot.ServerTimestampBehavior.ESTIMATE)
                        .sortedByDescending { (it.matchScore * 0.65) + (it.aestheticScore * 0.35) }
                }
        )
    }

    fun observeBrands(uid: String): Flow<List<BrandProfile>> = flow {
        require(uid.isNotBlank()) { "User ID must not be blank" }
        emitAll(
            userDoc(uid).collection("brands")
                .snapshots()
                .map { snap ->
                    snap.toObjects(BrandProfile::class.java, DocumentSnapshot.ServerTimestampBehavior.ESTIMATE)
                        .sortedByDescending { it.processedCount }
                }
        )
    }

    fun observeEngines(uid: String): Flow<List<EngineConfig>> = flow {
        require(uid.isNotBlank()) { "User ID must not be blank" }
        emitAll(
            userDoc(uid).collection("engines")
                .snapshots()
                .map { snap ->
                    snap.toObjects(EngineConfig::class.java, DocumentSnapshot.ServerTimestampBehavior.ESTIMATE)
                        .sortedBy { it.priorityOrder }
                }
        )
    }

    fun observeLogs(uid: String): Flow<List<EngineAuditLog>> = flow {
        require(uid.isNotBlank()) { "User ID must not be blank" }
        emitAll(
            userDoc(uid).collection("logs")
                .snapshots()
                .map { snap ->
                    snap.toObjects(EngineAuditLog::class.java, DocumentSnapshot.ServerTimestampBehavior.ESTIMATE)
                        .sortedByDescending { it.createdAt?.seconds ?: 0L }
                        .take(80)
                }
        )
    }

    suspend fun getBrandsOnce(uid: String): List<BrandProfile> = try {
        userDoc(uid).collection("brands").get().await()
            .toObjects(BrandProfile::class.java, DocumentSnapshot.ServerTimestampBehavior.ESTIMATE)
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        handleFirestoreError(e, OperationType.LIST, "users/$uid/brands")
        emptyList()
    }

    suspend fun getProductsOnce(uid: String): List<ProductRecord> = try {
        userDoc(uid).collection("products").get().await()
            .toObjects(ProductRecord::class.java, DocumentSnapshot.ServerTimestampBehavior.ESTIMATE)
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        handleFirestoreError(e, OperationType.LIST, "users/$uid/products")
        emptyList()
    }

    suspend fun getCandidatesOnce(uid: String, productId: String): List<DiscoveredImage> = try {
        userDoc(uid).collection("products").document(productId).collection("candidates")
            .get().await()
            .toObjects(DiscoveredImage::class.java, DocumentSnapshot.ServerTimestampBehavior.ESTIMATE)
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        handleFirestoreError(e, OperationType.LIST, "users/$uid/products/$productId/candidates")
        emptyList()
    }

    suspend fun createBatch(batch: BatchJob, batchId: String = "batch_${UUID.randomUUID().toString().take(10)}"): Result<String> {
        val uid = auth.currentUser?.uid ?: return Result.failure(IllegalStateException("غير مسجل الدخول"))
        val path = "users/$uid/batches/$batchId"
        return try {
            require(requireUserId() == uid)
            userDoc(uid).collection("batches").document(batchId)
                .set(batch.toCreateMap(uid))
                .await()
            Result.success(batchId)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            handleFirestoreError(e, OperationType.CREATE, path)
            Result.failure(e)
        }
    }

    suspend fun updateBatchProgress(
        batchId: String,
        status: BatchStatus,
        processed: Long,
        found: Long,
        review: Long,
        zero: Long,
        discoveredImages: Long
    ): Result<Unit> {
        val uid = auth.currentUser?.uid ?: return Result.failure(IllegalStateException("غير مسجل الدخول"))
        val path = "users/$uid/batches/$batchId"
        return try {
            require(requireUserId() == uid)
            userDoc(uid).collection("batches").document(batchId).update(
                mapOf(
                    "status" to status.name,
                    "processedProducts" to processed.coerceAtLeast(0L),
                    "foundProductsCount" to found.coerceAtLeast(0L),
                    "reviewProductsCount" to review.coerceAtLeast(0L),
                    "zeroResultCount" to zero.coerceAtLeast(0L),
                    "discoveredImagesCount" to discoveredImages.coerceAtLeast(0L),
                    "updatedAt" to FieldValue.serverTimestamp()
                )
            ).await()
            Result.success(Unit)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            handleFirestoreError(e, OperationType.UPDATE, path)
            Result.failure(e)
        }
    }

    suspend fun createProduct(
        product: ProductRecord,
        productId: String = "prod_${UUID.randomUUID().toString().take(10)}"
    ): Result<String> {
        val uid = auth.currentUser?.uid ?: return Result.failure(IllegalStateException("غير مسجل الدخول"))
        val path = "users/$uid/products/$productId"
        return try {
            require(requireUserId() == uid)
            userDoc(uid).collection("products").document(productId)
                .set(product.toCreateMap(uid))
                .await()
            Result.success(productId)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            handleFirestoreError(e, OperationType.CREATE, path)
            Result.failure(e)
        }
    }

    suspend fun updateProduct(productId: String, fields: Map<String, Any>): Result<Unit> {
        val uid = auth.currentUser?.uid ?: return Result.failure(IllegalStateException("غير مسجل الدخول"))
        val path = "users/$uid/products/$productId"
        return try {
            require(requireUserId() == uid)
            require(productId.isNotBlank())
            val payload = fields.toMutableMap().apply {
                remove("id")
                remove("userId")
                remove("createdAt")
                put("updatedAt", FieldValue.serverTimestamp())
            }
            userDoc(uid).collection("products").document(productId).update(payload).await()
            Result.success(Unit)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            handleFirestoreError(e, OperationType.UPDATE, path)
            Result.failure(e)
        }
    }

    suspend fun updateProductApproval(productId: String, approval: ApprovalStatus): Result<Unit> =
        updateProduct(productId, mapOf("approvalStatus" to approval.name))

    suspend fun saveCandidate(
        productId: String,
        candidate: DiscoveredImage,
        candidateId: String = "cand_${UUID.randomUUID().toString().take(10)}"
    ): Result<String> {
        val uid = auth.currentUser?.uid ?: return Result.failure(IllegalStateException("غير مسجل الدخول"))
        val path = "users/$uid/products/$productId/candidates/$candidateId"
        return try {
            require(requireUserId() == uid)
            userDoc(uid).collection("products").document(productId)
                .collection("candidates").document(candidateId)
                .set(candidate.copy(productId = productId).toCreateMap(uid))
                .await()
            Result.success(candidateId)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            handleFirestoreError(e, OperationType.CREATE, path)
            Result.failure(e)
        }
    }

    suspend fun updateCandidateDecision(
        productId: String,
        candidateId: String,
        decision: ReviewDecision,
        rejectionReason: String = "",
        localSavedPath: String? = null
    ): Result<Unit> {
        val uid = auth.currentUser?.uid ?: return Result.failure(IllegalStateException("غير مسجل الدخول"))
        val path = "users/$uid/products/$productId/candidates/$candidateId"
        return try {
            require(requireUserId() == uid)
            val updates = mutableMapOf<String, Any>(
                "reviewDecision" to decision.name,
                "rejectionReason" to rejectionReason.take(300),
                "updatedAt" to FieldValue.serverTimestamp()
            )
            if (localSavedPath != null) {
                updates["localSavedPath"] = localSavedPath.take(500)
            }
            userDoc(uid).collection("products").document(productId)
                .collection("candidates").document(candidateId)
                .update(updates)
                .await()
            Result.success(Unit)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            handleFirestoreError(e, OperationType.UPDATE, path)
            Result.failure(e)
        }
    }

    suspend fun upsertBrand(brand: BrandProfile): Result<Unit> {
        val uid = auth.currentUser?.uid ?: return Result.failure(IllegalStateException("غير مسجل الدخول"))
        val cleanId = brand.id.ifBlank {
            brand.brandName.lowercase().replace(Regex("[^a-z0-9]+"), "_").trim('_').ifBlank {
                "brand_${UUID.randomUUID().toString().take(8)}"
            }.take(64)
        }
        val path = "users/$uid/brands/$cleanId"
        return try {
            require(requireUserId() == uid)
            val ref = userDoc(uid).collection("brands").document(cleanId)
            val existing = ref.get().await()
            if (existing.exists()) {
                ref.update(
                    mapOf(
                        "brandName" to brand.brandName.take(120),
                        "officialWebsite" to brand.officialWebsite.take(500),
                        "instagramHandle" to brand.instagramHandle.take(120),
                        "pinterestHandle" to brand.pinterestHandle.take(120),
                        "trustedDomains" to brand.trustedDomains.take(20),
                        "successfulQueries" to brand.successfulQueries.take(20),
                        "processedCount" to brand.processedCount.coerceAtLeast(0L),
                        "successRate" to brand.successRate.coerceIn(0.0, 1.0),
                        "updatedAt" to FieldValue.serverTimestamp()
                    )
                ).await()
            } else {
                ref.set(brand.toCreateMap(uid)).await()
            }
            Result.success(Unit)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            handleFirestoreError(e, OperationType.WRITE, path)
            Result.failure(e)
        }
    }

    suspend fun saveEngineConfig(config: EngineConfig): Result<Unit> {
        val uid = auth.currentUser?.uid ?: return Result.failure(IllegalStateException("غير مسجل الدخول"))
        val docId = config.id.ifBlank { config.engineKey }
        val path = "users/$uid/engines/$docId"
        return try {
            require(requireUserId() == uid)
            val ref = userDoc(uid).collection("engines").document(docId)
            val existing = ref.get().await()
            if (existing.exists()) {
                ref.update(
                    mapOf(
                        "displayName" to config.displayName.take(100),
                        "category" to config.category.take(40),
                        "enabled" to config.enabled,
                        "priorityOrder" to config.priorityOrder.coerceIn(0L, 100L),
                        "costTier" to config.costTier.take(40),
                        "endpointUrl" to config.endpointUrl.take(500),
                        "lastHealthStatus" to config.lastHealthStatus.take(40),
                        "lastLatencyMs" to config.lastLatencyMs.coerceAtLeast(0L),
                        "lastTestSummary" to config.lastTestSummary.take(300),
                        "updatedAt" to FieldValue.serverTimestamp()
                    )
                ).await()
            } else {
                ref.set(config.toCreateMap(uid)).await()
            }
            Result.success(Unit)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            handleFirestoreError(e, OperationType.WRITE, path)
            Result.failure(e)
        }
    }

    suspend fun appendLog(level: String, component: String, message: String) {
        val uid = auth.currentUser?.uid ?: return
        val logId = "log_${System.currentTimeMillis()}_${UUID.randomUUID().toString().take(4)}"
        val path = "users/$uid/logs/$logId"
        try {
            userDoc(uid).collection("logs").document(logId)
                .set(EngineAuditLog(level = level, component = component, message = message).toCreateMap(uid))
                .await()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            handleFirestoreError(e, OperationType.CREATE, path)
        }
    }

    suspend fun ensureDefaultEnginesSeeded(uid: String) {
        try {
            val snap = userDoc(uid).collection("engines").get().await()
            if (!snap.isEmpty) return
            val defaults = listOf(
                EngineConfig(
                    id = "gemini_vision",
                    engineKey = "gemini_vision",
                    displayName = "Gemini 3.8 Flash Vision & OCR",
                    category = "VISION",
                    enabled = true,
                    priorityOrder = 1,
                    costTier = "FREE_TIER_CLOUD",
                    lastHealthStatus = "READY",
                    lastTestSummary = "تحليل الهوية التجارية وقراءة العربية والإنجليزية"
                ),
                EngineConfig(
                    id = "zxing_barcode",
                    engineKey = "zxing_barcode",
                    displayName = "ZXing On-Device Barcode",
                    category = "BARCODE",
                    enabled = true,
                    priorityOrder = 2,
                    costTier = "FREE_LOCAL",
                    lastHealthStatus = "READY",
                    lastTestSummary = "قراءة EAN-13 / UPC-A / QR محليًا (Apache-2.0)"
                ),
                EngineConfig(
                    id = "open_beauty_facts",
                    engineKey = "open_beauty_facts",
                    displayName = "Open Beauty Facts API",
                    category = "TEXT_SEARCH",
                    enabled = true,
                    priorityOrder = 3,
                    costTier = "FREE_API",
                    endpointUrl = "https://world.openbeautyfacts.org",
                    lastHealthStatus = "READY",
                    lastTestSummary = "قاعدة بيانات مفتوحة لمستحضرات التجميل والباركود"
                ),
                EngineConfig(
                    id = "openverse_cc",
                    engineKey = "openverse_cc",
                    displayName = "Openverse Creative Commons",
                    category = "TEXT_SEARCH",
                    enabled = true,
                    priorityOrder = 4,
                    costTier = "FREE_API",
                    endpointUrl = "https://api.openverse.org",
                    lastHealthStatus = "READY",
                    lastTestSummary = "صور مفتوحة المصدر مع بيانات الترخيص"
                ),
                EngineConfig(
                    id = "wikimedia_commons",
                    engineKey = "wikimedia_commons",
                    displayName = "Wikimedia Commons Media API",
                    category = "TEXT_SEARCH",
                    enabled = true,
                    priorityOrder = 5,
                    costTier = "FREE_API",
                    endpointUrl = "https://commons.wikimedia.org",
                    lastHealthStatus = "READY",
                    lastTestSummary = "صور منتجات وعلامات مع حقوق استخدام واضحة"
                ),
                EngineConfig(
                    id = "searxng_meta",
                    engineKey = "searxng_meta",
                    displayName = "SearXNG Meta-Search Adapter",
                    category = "SOCIAL_SEARCH",
                    enabled = true,
                    priorityOrder = 6,
                    costTier = "FREE_LOCAL",
                    endpointUrl = "",
                    lastHealthStatus = "UNCONFIGURED",
                    lastTestSummary = "أضف رابط خادم SearXNG الخاص بك لتفعيل البحث الموسع"
                ),
                EngineConfig(
                    id = "social_index",
                    engineKey = "social_index",
                    displayName = "Instagram & Pinterest Public Index",
                    category = "SOCIAL_SEARCH",
                    enabled = true,
                    priorityOrder = 7,
                    costTier = "FREE_API",
                    lastHealthStatus = "READY",
                    lastTestSummary = "روابط استكشاف عام وحفظ الروابط دون تجاوز المصادقة"
                ),
                EngineConfig(
                    id = "creative_studio",
                    engineKey = "creative_studio",
                    displayName = "AI Creative Studio (Nano Banana 2.1)",
                    category = "CREATIVE_STUDIO",
                    enabled = true,
                    priorityOrder = 8,
                    costTier = "OPTIONAL_BLAZE",
                    lastHealthStatus = "READY",
                    lastTestSummary = "وحدة ثانوية اختيارية للمنتجات ذات النتيجة صفر"
                )
            )
            defaults.forEach { saveEngineConfig(it) }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            handleFirestoreError(e, OperationType.WRITE, "users/$uid/engines")
        }
    }
}
