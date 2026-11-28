package com.example.model

import androidx.annotation.Keep
import com.google.firebase.Timestamp
import com.google.firebase.firestore.DocumentId
import com.google.firebase.firestore.FieldValue
import com.google.firebase.firestore.IgnoreExtraProperties
import com.google.firebase.firestore.ServerTimestamp

enum class BatchStatus(val labelAr: String) {
    QUEUED("في الانتظار"),
    RUNNING("قيد المعالجة"),
    PAUSED("متوقف مؤقتًا"),
    COMPLETED("مكتمل"),
    CANCELLED("ملغى"),
    FAILED("فشل")
}

enum class SearchStrategy(val labelAr: String, val descriptionAr: String) {
    STANDARD("تصاعدي متوازن (L0-L5)", "الذاكرة المحلية ثم الباركود والاسم ثم المصادر المفتوحة"),
    OFFICIAL_FIRST("المصادر الرسمية أولاً", "الأولوية لمواقع الماركات وقواعد البيانات التجميلية"),
    DEEP_SOCIAL("بحث موسّع + اجتماعي", "يشمل فهرسة Instagram وPinterest وSearXNG"),
    FAST_BARCODE("بحث سريع بالباركود", "يعتمد على الباركود والذاكرة التراكمية والاسم المباشر")
}

enum class ProductStatus(val labelAr: String) {
    PENDING("قيد الانتظار"),
    IDENTIFYING("تحليل الهوية"),
    SEARCHING("جاري البحث"),
    VERIFYING("التحقق البصري"),
    FOUND("تم العثور على صور"),
    REVIEW_REQUIRED("يحتاج مراجعة"),
    ZERO_RESULT("النتيجة صفر"),
    FAILED("فشل المعالجة")
}

enum class ZeroResultReason(val labelAr: String) {
    NONE("لا يوجد"),
    NO_MATCHING_IMAGES("لم توجد صور مطابقة للمنتج"),
    LOW_QUALITY_ONLY("توجد صور لكنها منخفضة الجودة"),
    RIGHTS_UNCLEAR("توجد صور لكن الحقوق غير واضحة أو مقيدة"),
    LINK_ONLY_SOURCES("توجد روابط صفحات دون إمكانية تنزيل مباشرة"),
    UNCERTAIN_IDENTITY("هوية المنتج غير مؤكدة من الصورة الأصلية"),
    SOURCE_UNREACHABLE("تعذر الوصول إلى مصادر البحث"),
    ENGINE_DOWN("توقفت بعض محركات البحث"),
    INCOMPLETE_PROCESSING("لم تكتمل المعالجة")
}

enum class ApprovalStatus(val labelAr: String) {
    PENDING("بانتظار الاعتماد"),
    APPROVED("معتمد للمتجر"),
    REJECTED("مرفوض"),
    SENT_TO_STUDIO("أُرسل للاستوديو")
}

enum class SourceType(val labelAr: String) {
    OFFICIAL_BRAND("الموقع الرسمي للماركة"),
    OPEN_BEAUTY_DB("Open Beauty Facts"),
    OPEN_MEDIA("مصادر مفتوحة مرخصة"),
    SOCIAL_INDEX("فهرس اجتماعي عام"),
    SEARCH_ENGINE("محرك بحث متعدد"),
    CREATIVE_STUDIO("الاستوديو الإبداعي")
}

enum class ImageCategory(val code: String, val labelAr: String) {
    A_OFFICIAL("A", "صورة رسمية للمنتج"),
    B_MARKETING("B", "صورة تسويقية احترافية"),
    C_LIFESTYLE("C", "صورة إبداعية Lifestyle"),
    D_WHITE_BG("D", "صورة بخلفية بيضاء"),
    E_PACKAGING("E", "صورة توضيحية للعبوة"),
    F_LOW_QUALITY("F", "صورة منخفضة الجودة"),
    G_MISMATCH("G", "صورة غير مطابقة"),
    H_REVIEW("H", "تحتاج مراجعة")
}

enum class RightsStatus(val labelAr: String) {
    COMMERCIAL_PERMITTED("مسموح بالاستخدام التجاري"),
    PERMISSION_REQUIRED("يتطلب إذن المالك"),
    RIGHTS_UNKNOWN("الحقوق غير واضحة"),
    RESTRICTED("استخدام مقيد"),
    LINK_ONLY("حفظ الرابط فقط")
}

enum class ReviewDecision(val labelAr: String) {
    PENDING("قيد المراجعة"),
    APPROVED("معتمد"),
    REJECTED("مرفوض")
}

inline fun <reified T : Enum<T>> safeEnumValueOf(raw: String?, default: T): T {
    if (raw.isNullOrBlank()) return default
    return enumValues<T>().firstOrNull { it.name.equals(raw.trim(), ignoreCase = true) } ?: default
}

@Keep
@IgnoreExtraProperties
data class BatchJob(
    @DocumentId val id: String = "",
    val userId: String = "",
    val title: String = "",
    val status: String = BatchStatus.QUEUED.name,
    val strategy: String = SearchStrategy.STANDARD.name,
    val targetImagesPerProduct: Long = 5L,
    val totalProducts: Long = 0L,
    val processedProducts: Long = 0L,
    val foundProductsCount: Long = 0L,
    val reviewProductsCount: Long = 0L,
    val zeroResultCount: Long = 0L,
    val discoveredImagesCount: Long = 0L,
    @ServerTimestamp val createdAt: Timestamp? = null,
    @ServerTimestamp val updatedAt: Timestamp? = null
) {
    fun statusEnum(): BatchStatus = safeEnumValueOf(status, BatchStatus.QUEUED)
    fun strategyEnum(): SearchStrategy = safeEnumValueOf(strategy, SearchStrategy.STANDARD)

    fun toCreateMap(uid: String): Map<String, Any> = mapOf(
        "userId" to uid,
        "title" to title.take(120).ifBlank { "دفعة منتجات" },
        "status" to status,
        "strategy" to strategy,
        "targetImagesPerProduct" to targetImagesPerProduct.coerceIn(1L, 20L),
        "totalProducts" to totalProducts.coerceAtLeast(0L),
        "processedProducts" to processedProducts.coerceAtLeast(0L),
        "foundProductsCount" to foundProductsCount.coerceAtLeast(0L),
        "reviewProductsCount" to reviewProductsCount.coerceAtLeast(0L),
        "zeroResultCount" to zeroResultCount.coerceAtLeast(0L),
        "discoveredImagesCount" to discoveredImagesCount.coerceAtLeast(0L),
        "createdAt" to FieldValue.serverTimestamp(),
        "updatedAt" to FieldValue.serverTimestamp()
    )
}

@Keep
@IgnoreExtraProperties
data class ProductRecord(
    @DocumentId val id: String = "",
    val userId: String = "",
    val batchId: String = "",
    val skuCode: String = "",
    val barcode: String = "",
    val brand: String = "",
    val productNameEn: String = "",
    val productNameAr: String = "",
    val manufacturer: String = "",
    val category: String = "",
    val variantEdition: String = "",
    val sizeWeight: String = "",
    val shadeColor: String = "",
    val packagingType: String = "",
    val extractedTextSummary: String = "",
    val identityConfidence: Double = 0.0,
    val visualSignatureHash: String = "",
    val localOriginalPaths: List<String> = emptyList(),
    val searchQueries: List<String> = emptyList(),
    val status: String = ProductStatus.PENDING.name,
    val zeroResultReason: String = ZeroResultReason.NONE.name,
    val escalationLevelReached: String = "L0",
    val approvalStatus: String = ApprovalStatus.PENDING.name,
    val orchestratorNotes: String = "",
    val discoveredCount: Long = 0L,
    val matchedCount: Long = 0L,
    val bestImageUrl: String = "",
    @ServerTimestamp val createdAt: Timestamp? = null,
    @ServerTimestamp val updatedAt: Timestamp? = null
) {
    fun statusEnum(): ProductStatus = safeEnumValueOf(status, ProductStatus.PENDING)
    fun zeroReasonEnum(): ZeroResultReason = safeEnumValueOf(zeroResultReason, ZeroResultReason.NONE)
    fun approvalEnum(): ApprovalStatus = safeEnumValueOf(approvalStatus, ApprovalStatus.PENDING)

    fun displayTitle(): String = when {
        productNameAr.isNotBlank() && brand.isNotBlank() -> "$brand - $productNameAr"
        productNameEn.isNotBlank() && brand.isNotBlank() -> "$brand - $productNameEn"
        productNameAr.isNotBlank() -> productNameAr
        productNameEn.isNotBlank() -> productNameEn
        brand.isNotBlank() -> brand
        skuCode.isNotBlank() -> "SKU: $skuCode"
        barcode.isNotBlank() -> "باركود: $barcode"
        else -> "منتج قيد التعرف"
    }

    fun toCreateMap(uid: String): Map<String, Any> {
        val raw = mutableMapOf<String, Any?>(
            "userId" to uid,
            "batchId" to batchId,
            "skuCode" to skuCode.take(120),
            "barcode" to barcode.take(64),
            "brand" to brand.take(120),
            "productNameEn" to productNameEn.take(200),
            "productNameAr" to productNameAr.take(200),
            "manufacturer" to manufacturer.take(120),
            "category" to category.take(80),
            "variantEdition" to variantEdition.take(120),
            "sizeWeight" to sizeWeight.take(64),
            "shadeColor" to shadeColor.take(80),
            "packagingType" to packagingType.take(80),
            "extractedTextSummary" to extractedTextSummary.take(1000),
            "identityConfidence" to identityConfidence.coerceIn(0.0, 1.0),
            "visualSignatureHash" to visualSignatureHash.take(64),
            "localOriginalPaths" to localOriginalPaths.take(10),
            "searchQueries" to searchQueries.take(15),
            "status" to status,
            "zeroResultReason" to zeroResultReason,
            "escalationLevelReached" to escalationLevelReached.take(16),
            "approvalStatus" to approvalStatus,
            "orchestratorNotes" to orchestratorNotes.take(1000),
            "discoveredCount" to discoveredCount.coerceAtLeast(0L),
            "matchedCount" to matchedCount.coerceAtLeast(0L),
            "bestImageUrl" to bestImageUrl.take(1000),
            "createdAt" to FieldValue.serverTimestamp(),
            "updatedAt" to FieldValue.serverTimestamp()
        )
        @Suppress("UNCHECKED_CAST")
        return raw.filterValues { it != null } as Map<String, Any>
    }
}

@Keep
@IgnoreExtraProperties
data class DiscoveredImage(
    @DocumentId val id: String = "",
    val userId: String = "",
    val productId: String = "",
    val imageUrl: String = "",
    val pageUrl: String = "",
    val sourceName: String = "",
    val publisherName: String = "",
    val sourceType: String = SourceType.OPEN_MEDIA.name,
    val imageCategory: String = ImageCategory.H_REVIEW.name,
    val rightsStatus: String = RightsStatus.RIGHTS_UNKNOWN.name,
    val licenseName: String = "",
    val matchScore: Double = 0.0,
    val brandMatchScore: Double = 0.0,
    val skuMatchScore: Double = 0.0,
    val aestheticScore: Double = 0.0,
    val widthPx: Long = 0L,
    val heightPx: Long = 0L,
    val perceptualHash: String = "",
    val verificationNotes: String = "",
    val reviewDecision: String = ReviewDecision.PENDING.name,
    val rejectionReason: String = "",
    val localSavedPath: String = "",
    @ServerTimestamp val createdAt: Timestamp? = null,
    @ServerTimestamp val updatedAt: Timestamp? = null
) {
    fun sourceTypeEnum(): SourceType = safeEnumValueOf(sourceType, SourceType.OPEN_MEDIA)
    fun categoryEnum(): ImageCategory = safeEnumValueOf(imageCategory, ImageCategory.H_REVIEW)
    fun rightsEnum(): RightsStatus = safeEnumValueOf(rightsStatus, RightsStatus.RIGHTS_UNKNOWN)
    fun decisionEnum(): ReviewDecision = safeEnumValueOf(reviewDecision, ReviewDecision.PENDING)

    fun toCreateMap(uid: String): Map<String, Any> {
        val raw = mutableMapOf<String, Any?>(
            "userId" to uid,
            "productId" to productId,
            "imageUrl" to imageUrl.take(1500),
            "pageUrl" to pageUrl.take(1500),
            "sourceName" to sourceName.take(100).ifBlank { "مصدر خارجي" },
            "publisherName" to publisherName.take(150),
            "sourceType" to sourceType,
            "imageCategory" to imageCategory,
            "rightsStatus" to rightsStatus,
            "licenseName" to licenseName.take(120),
            "matchScore" to matchScore.coerceIn(0.0, 1.0),
            "brandMatchScore" to brandMatchScore.coerceIn(0.0, 1.0),
            "skuMatchScore" to skuMatchScore.coerceIn(0.0, 1.0),
            "aestheticScore" to aestheticScore.coerceIn(0.0, 1.0),
            "widthPx" to widthPx.coerceAtLeast(0L),
            "heightPx" to heightPx.coerceAtLeast(0L),
            "perceptualHash" to perceptualHash.take(64),
            "verificationNotes" to verificationNotes.take(600),
            "reviewDecision" to reviewDecision,
            "rejectionReason" to rejectionReason.take(300),
            "localSavedPath" to localSavedPath.take(500),
            "createdAt" to FieldValue.serverTimestamp(),
            "updatedAt" to FieldValue.serverTimestamp()
        )
        @Suppress("UNCHECKED_CAST")
        return raw.filterValues { it != null } as Map<String, Any>
    }
}

@Keep
@IgnoreExtraProperties
data class BrandProfile(
    @DocumentId val id: String = "",
    val userId: String = "",
    val brandName: String = "",
    val officialWebsite: String = "",
    val instagramHandle: String = "",
    val pinterestHandle: String = "",
    val trustedDomains: List<String> = emptyList(),
    val successfulQueries: List<String> = emptyList(),
    val processedCount: Long = 0L,
    val successRate: Double = 0.0,
    @ServerTimestamp val createdAt: Timestamp? = null,
    @ServerTimestamp val updatedAt: Timestamp? = null
) {
    fun toCreateMap(uid: String): Map<String, Any> = mapOf(
        "userId" to uid,
        "brandName" to brandName.take(120).ifBlank { "Unknown Brand" },
        "officialWebsite" to officialWebsite.take(500),
        "instagramHandle" to instagramHandle.take(120),
        "pinterestHandle" to pinterestHandle.take(120),
        "trustedDomains" to trustedDomains.take(20),
        "successfulQueries" to successfulQueries.take(20),
        "processedCount" to processedCount.coerceAtLeast(0L),
        "successRate" to successRate.coerceIn(0.0, 1.0),
        "createdAt" to FieldValue.serverTimestamp(),
        "updatedAt" to FieldValue.serverTimestamp()
    )
}

@Keep
@IgnoreExtraProperties
data class EngineConfig(
    @DocumentId val id: String = "",
    val userId: String = "",
    val engineKey: String = "",
    val displayName: String = "",
    val category: String = "",
    val enabled: Boolean = true,
    val priorityOrder: Long = 10L,
    val costTier: String = "FREE_API",
    val endpointUrl: String = "",
    val lastHealthStatus: String = "READY",
    val lastLatencyMs: Long = 0L,
    val lastTestSummary: String = "",
    @ServerTimestamp val createdAt: Timestamp? = null,
    @ServerTimestamp val updatedAt: Timestamp? = null
) {
    fun toCreateMap(uid: String): Map<String, Any> = mapOf(
        "userId" to uid,
        "engineKey" to engineKey.take(64),
        "displayName" to displayName.take(100),
        "category" to category.take(40),
        "enabled" to enabled,
        "priorityOrder" to priorityOrder.coerceIn(0L, 100L),
        "costTier" to costTier.take(40),
        "endpointUrl" to endpointUrl.take(500),
        "lastHealthStatus" to lastHealthStatus.take(40),
        "lastLatencyMs" to lastLatencyMs.coerceAtLeast(0L),
        "lastTestSummary" to lastTestSummary.take(300),
        "createdAt" to FieldValue.serverTimestamp(),
        "updatedAt" to FieldValue.serverTimestamp()
    )
}

@Keep
@IgnoreExtraProperties
data class EngineAuditLog(
    @DocumentId val id: String = "",
    val userId: String = "",
    val level: String = "INFO",
    val component: String = "",
    val message: String = "",
    @ServerTimestamp val createdAt: Timestamp? = null
) {
    fun toCreateMap(uid: String): Map<String, Any> = mapOf(
        "userId" to uid,
        "level" to level,
        "component" to component.take(80).ifBlank { "System" },
        "message" to message.take(800),
        "createdAt" to FieldValue.serverTimestamp()
    )
}

sealed interface UiState<out T> {
    data object Loading : UiState<Nothing>
    data class Success<T>(val data: T) : UiState<T>
    data class Error(val message: String) : UiState<Nothing>
}
