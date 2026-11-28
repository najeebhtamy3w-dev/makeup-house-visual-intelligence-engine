package com.example.engine

import android.graphics.Bitmap
import android.util.Log
import com.example.core.SecurityAndImageUtils
import com.example.model.ImageCategory
import com.example.model.ProductRecord
import com.example.model.safeEnumValueOf
import com.google.firebase.Firebase
import com.google.firebase.ai.ai
import com.google.firebase.ai.type.ImagePart
import com.google.firebase.ai.type.ResponseModality
import com.google.firebase.ai.type.Schema
import com.google.firebase.ai.type.content
import com.google.firebase.ai.type.generationConfig
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.withTimeout
import org.json.JSONObject

class GeminiVerificationAndScoringEngine : ProductMatchingProvider {
    override val providerKey: String = "gemini_verification"

    private val verificationSchema = Schema.obj(
        properties = mapOf(
            "isMatch" to Schema.boolean(description = "True ONLY if the candidate depicts the exact same cosmetic product SKU (same brand, product line, edition, size, shade)"),
            "brandMatchScore" to Schema.double(description = "0.0 to 1.0 brand match certainty"),
            "skuMatchScore" to Schema.double(description = "0.0 to 1.0 exact product, edition, size, and shade match"),
            "overallMatchScore" to Schema.double(description = "0.0 to 1.0 combined product identity match score"),
            "marketingAestheticScore" to Schema.double(description = "0.0 to 1.0 commercial e-commerce appeal, lighting, composition, and background cleanliness"),
            "hasWatermark" to Schema.boolean(description = "True if visible stock/store watermark is present"),
            "imageCategory" to Schema.enumeration(
                values = listOf(
                    "A_OFFICIAL",
                    "B_MARKETING",
                    "C_LIFESTYLE",
                    "D_WHITE_BG",
                    "E_PACKAGING",
                    "F_LOW_QUALITY",
                    "G_MISMATCH",
                    "H_REVIEW"
                ),
                description = "Commercial image classification"
            ),
            "notes" to Schema.string(description = "Concise Arabic explanation of why the candidate matched, needs review, or was rejected")
        )
    )

    private val verifyModel by lazy {
        Firebase.ai.generativeModel(
            modelName = "gemini-3.8-flash",
            generationConfig = generationConfig {
                responseMimeType = "application/json"
                responseSchema = verificationSchema
            }
        )
    }

    override suspend fun verifyCandidate(
        originalBitmap: Bitmap,
        candidateBitmap: Bitmap?,
        product: ProductRecord,
        hit: CandidateSearchHit
    ): ProductVerificationResult {
        val techMetrics = candidateBitmap?.let { SecurityAndImageUtils.evaluateTechnicalQuality(it) }
        val localTechScore = if (techMetrics != null) {
            (techMetrics.resolutionScore * 0.45 + techMetrics.sharpnessScore * 0.30 + techMetrics.exposureScore * 0.25)
                .coerceIn(0.0, 1.0)
        } else 0.4

        return try {
            val response = withTimeout(45_000L) {
                verifyModel.generateContent(
                    content {
                        text("Image 1 (Original Store Photo):")
                        image(originalBitmap)
                        if (candidateBitmap != null) {
                            text("Image 2 (Candidate Discovered Image):")
                            image(candidateBitmap)
                        }
                        text(
                            buildString {
                                appendLine("Verify whether the candidate image represents the EXACT same product as Image 1.")
                                appendLine("Product Identity: Brand='${product.brand}', NameEn='${product.productNameEn}', Variant='${product.variantEdition}', Size='${product.sizeWeight}', Shade='${product.shadeColor}', Barcode='${product.barcode}'")
                                appendLine("Candidate Title='${hit.candidateTitle}', Source='${hit.sourceName}'")
                                appendLine("Rules:")
                                appendLine("- Different product from the same brand -> isMatch=false, imageCategory=G_MISMATCH.")
                                appendLine("- Different size or different makeup shade -> isMatch=false, imageCategory=G_MISMATCH.")
                                appendLine("- Background/lighting/props (flowers, lifestyle flatlay) MAY differ if the bottle/packaging identity matches!")
                                appendLine("- Aesthetic score must NEVER override identity mismatch.")
                            }
                        )
                    }
                )
            }
            val json = JSONObject(response.text ?: "{}")
            val isMatch = json.optBoolean("isMatch", false)
            val brandScore = json.optDouble("brandMatchScore", 0.0).coerceIn(0.0, 1.0)
            val skuScore = json.optDouble("skuMatchScore", 0.0).coerceIn(0.0, 1.0)
            val matchScore = json.optDouble("overallMatchScore", 0.0).coerceIn(0.0, 1.0)
            val aiAesthetic = json.optDouble("marketingAestheticScore", localTechScore).coerceIn(0.0, 1.0)
            val hasWatermark = json.optBoolean("hasWatermark", false)
            val rawCat = json.optString("imageCategory", "H_REVIEW")
            val category = safeEnumValueOf(rawCat, ImageCategory.H_REVIEW)
            val combinedAesthetic = if (hasWatermark) {
                (aiAesthetic * 0.4 + localTechScore * 0.2).coerceAtMost(0.45)
            } else {
                (aiAesthetic * 0.6 + localTechScore * 0.4).coerceIn(0.0, 1.0)
            }

            ProductVerificationResult(
                isMatch = isMatch && !hasWatermark,
                matchScore = matchScore,
                brandMatchScore = brandScore,
                skuMatchScore = skuScore,
                aestheticScore = combinedAesthetic,
                imageCategory = if (!isMatch) ImageCategory.G_MISMATCH else category,
                hasWatermark = hasWatermark,
                notes = json.optString("notes", "").ifBlank { "تم التقييم عبر محرك التحقق البصري" }
            )
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            Log.w(TAG, "AI verification fallback to deterministic metrics: ${e.message}")
            // Honest fallback: mark for manual review rather than fabricating high match confidence
            val titleTokens = hit.candidateTitle.lowercase()
            val brandHit = product.brand.isNotBlank() && titleTokens.contains(product.brand.lowercase())
            val score = if (brandHit) 0.52 else 0.35
            ProductVerificationResult(
                isMatch = false,
                matchScore = score,
                brandMatchScore = if (brandHit) 0.7 else 0.2,
                skuMatchScore = 0.3,
                aestheticScore = localTechScore,
                imageCategory = ImageCategory.H_REVIEW,
                hasWatermark = false,
                notes = "يتطلب مراجعة يدوية (تعذر التحقق العميق بالذكاء الاصطناعي)"
            )
        }
    }

    private companion object {
        const val TAG = "GeminiVerification"
    }
}

class CreativeStudioProvider {
    private val imageModel by lazy {
        Firebase.ai.generativeModel(
            modelName = "gemini-nano-banana-2.1",
            generationConfig = generationConfig {
                responseModalities = listOf(ResponseModality.IMAGE)
            }
        )
    }

    suspend fun generateStudioScene(
        originalBitmap: Bitmap,
        product: ProductRecord,
        stylePreset: String
    ): Result<Bitmap> {
        return try {
            val prompt = buildString {
                appendLine("Create a professional commercial e-commerce product photograph featuring the EXACT cosmetic product shown in the input image.")
                appendLine("STRICT IDENTITY PRESERVATION: Do NOT alter the product bottle shape, cap, logo, brand name ('${product.brand}'), product label text, shade color, or packaging proportions.")
                appendLine("Style preset: $stylePreset.")
                appendLine("Studio lighting, crisp reflections, clean commercial composition suitable for a luxury beauty online store.")
            }
            val response = withTimeout(60_000L) {
                imageModel.generateContent(
                    content {
                        image(originalBitmap)
                        text(prompt)
                    }
                )
            }
            val bitmap = response.candidates.firstOrNull()
                ?.content?.parts?.filterIsInstance<ImagePart>()
                ?.firstOrNull()?.image
                ?: return Result.failure(IllegalStateException("لم يُرجع نموذج الاستوديو صورة (قد يتطلب المشروع خطة Firebase Blaze لتوليد الصور)"))
            Result.success(bitmap)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            Log.e("CreativeStudio", "Studio generation failed", e)
            Result.failure(e)
        }
    }
}
