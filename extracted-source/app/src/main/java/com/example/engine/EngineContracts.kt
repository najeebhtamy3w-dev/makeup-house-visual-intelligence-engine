package com.example.engine

import android.graphics.Bitmap
import com.example.model.ImageCategory
import com.example.model.ProductRecord
import com.example.model.RightsStatus
import com.example.model.SourceType

data class ProductIdentityExtraction(
    val brand: String,
    val productNameEn: String,
    val productNameAr: String,
    val manufacturer: String,
    val category: String,
    val variantEdition: String,
    val sizeWeight: String,
    val shadeColor: String,
    val packagingType: String,
    val visibleBarcode: String,
    val extractedTextSummary: String,
    val confidence: Double,
    val searchQueries: List<String>
)

data class CandidateSearchHit(
    val imageUrl: String,
    val pageUrl: String,
    val sourceName: String,
    val publisherName: String,
    val sourceType: SourceType,
    val rightsStatus: RightsStatus,
    val licenseName: String,
    val candidateTitle: String,
    val widthPx: Int = 0,
    val heightPx: Int = 0
)

data class ProductVerificationResult(
    val isMatch: Boolean,
    val matchScore: Double,
    val brandMatchScore: Double,
    val skuMatchScore: Double,
    val aestheticScore: Double,
    val imageCategory: ImageCategory,
    val hasWatermark: Boolean,
    val notes: String
)

data class EngineBenchmarkResult(
    val engineKey: String,
    val success: Boolean,
    val latencyMs: Long,
    val hitCount: Int,
    val summary: String
)

interface VisionProvider {
    val providerKey: String
    suspend fun identifyProduct(bitmaps: List<Bitmap>, hintBarcode: String, hintText: String): Result<ProductIdentityExtraction>
}

interface BarcodeProvider {
    val providerKey: String
    fun decodeBarcode(bitmaps: List<Bitmap>): String
}

interface ImageSearchProvider {
    val providerKey: String
    val displayName: String
    suspend fun search(product: ProductRecord, query: String, customEndpoint: String = ""): Result<List<CandidateSearchHit>>
    suspend fun healthCheck(customEndpoint: String = ""): EngineBenchmarkResult
}

interface ProductMatchingProvider {
    val providerKey: String
    suspend fun verifyCandidate(
        originalBitmap: Bitmap,
        candidateBitmap: Bitmap?,
        product: ProductRecord,
        hit: CandidateSearchHit
    ): ProductVerificationResult
}
