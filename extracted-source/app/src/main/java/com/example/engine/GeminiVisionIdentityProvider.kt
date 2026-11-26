package com.example.engine

import android.graphics.Bitmap
import android.util.Log
import com.google.firebase.Firebase
import com.google.firebase.ai.ai
import com.google.firebase.ai.type.Schema
import com.google.firebase.ai.type.content
import com.google.firebase.ai.type.generationConfig
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.withTimeout
import org.json.JSONObject

class GeminiVisionIdentityProvider : VisionProvider {
    override val providerKey: String = "gemini_vision"

    private val identitySchema = Schema.obj(
        properties = mapOf(
            "brand" to Schema.string(description = "Official brand name if visible or clearly identifiable; empty if unknown"),
            "productNameEn" to Schema.string(description = "Official commercial product name in English as printed or verified; empty if uncertain"),
            "productNameAr" to Schema.string(description = "Accurate Arabic product name/description without inventing facts"),
            "manufacturer" to Schema.string(description = "Manufacturer or parent company if visible; empty if unknown"),
            "category" to Schema.string(description = "Cosmetic category e.g. Skincare, Makeup, Haircare, Fragrance, Bodycare, Tools"),
            "variantEdition" to Schema.string(description = "Edition or formula variant e.g. SPF 50, Matte, Waterproof, Intense; empty if none"),
            "sizeWeight" to Schema.string(description = "Net volume or weight printed on packaging e.g. 236ml, 50g, 30ml; empty if not visible"),
            "shadeColor" to Schema.string(description = "Makeup shade name or number if printed e.g. 120 Classic Ivory; empty if not applicable"),
            "packagingType" to Schema.string(description = "Packaging form e.g. Pump Bottle, Tube, Dropper, Compact, Jar, Lipstick"),
            "visibleBarcode" to Schema.string(description = "Digits of any visible barcode printed on label; empty if unreadable"),
            "extractedTextSummary" to Schema.string(description = "Verbatim key printed text read via OCR (Arabic/English/French) from the packaging"),
            "confidence" to Schema.double(description = "Overall identity certainty from 0.0 to 1.0"),
            "searchQueries" to Schema.array(
                items = Schema.string(),
                description = "3 to 6 high-precision search queries combining brand, product name, size, shade, and commercial photography terms"
            )
        )
    )

    private val model by lazy {
        Firebase.ai.generativeModel(
            modelName = "gemini-3.8-flash",
            generationConfig = generationConfig {
                responseMimeType = "application/json"
                responseSchema = identitySchema
            }
        )
    }

    override suspend fun identifyProduct(
        bitmaps: List<Bitmap>,
        hintBarcode: String,
        hintText: String
    ): Result<ProductIdentityExtraction> {
        if (bitmaps.isEmpty()) {
            return Result.failure(IllegalArgumentException("لا توجد صور لتحليل المنتج"))
        }
        return try {
            val response = withTimeout(60_000L) {
                model.generateContent(
                    content {
                        bitmaps.take(4).forEach { image(it) }
                        text(
                            buildString {
                                appendLine("You are the Makeup House Product Identity Intelligence Engine.")
                                appendLine("Analyze these store-captured cosmetic/beauty product photos carefully (front, back, or barcode views).")
                                appendLine("STRICT ANTI-HALLUCINATION RULE: Never invent brand names, product names, sizes, shades, or barcodes.")
                                appendLine("If any attribute is not clearly printed or recognizable, leave it empty string \"\" and lower confidence accordingly.")
                                appendLine("Read all printed text in English, Arabic, French, or Korean accurately.")
                                if (hintBarcode.isNotBlank()) {
                                    appendLine("Decoded barcode hint (ZXing): $hintBarcode")
                                }
                                if (hintText.isNotBlank()) {
                                    appendLine("Additional CSV/SKU hint: $hintText")
                                }
                                appendLine("Generate 3 to 6 realistic commercial image search queries (clean English product name + brand + size/shade, plus queries with 'official product photography' or 'beauty campaign').")
                            }
                        )
                    }
                )
            }
            val jsonStr = response.text ?: throw IllegalStateException("استجابة فارغة من محرك الرؤية")
            val obj = JSONObject(jsonStr)
            val queriesJson = obj.optJSONArray("searchQueries")
            val queries = buildList {
                if (queriesJson != null) {
                    for (i in 0 until queriesJson.length()) {
                        val q = queriesJson.optString(i).trim()
                        if (q.isNotBlank()) add(q)
                    }
                }
            }
            val extraction = ProductIdentityExtraction(
                brand = obj.optString("brand", "").trim(),
                productNameEn = obj.optString("productNameEn", "").trim(),
                productNameAr = obj.optString("productNameAr", "").trim(),
                manufacturer = obj.optString("manufacturer", "").trim(),
                category = obj.optString("category", "").trim(),
                variantEdition = obj.optString("variantEdition", "").trim(),
                sizeWeight = obj.optString("sizeWeight", "").trim(),
                shadeColor = obj.optString("shadeColor", "").trim(),
                packagingType = obj.optString("packagingType", "").trim(),
                visibleBarcode = obj.optString("visibleBarcode", "").trim().ifBlank { hintBarcode },
                extractedTextSummary = obj.optString("extractedTextSummary", "").trim(),
                confidence = obj.optDouble("confidence", 0.5).coerceIn(0.0, 1.0),
                searchQueries = queries.distinct().take(8)
            )
            Result.success(extraction)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            Log.e(TAG, "Product identity analysis failed", e)
            Result.failure(e)
        }
    }

    suspend fun healthCheck(): EngineBenchmarkResult {
        val start = System.currentTimeMillis()
        return try {
            val res = withTimeout(30_000L) {
                Firebase.ai.generativeModel("gemini-3.8-flash")
                    .generateContent("Reply with OK")
            }
            val elapsed = System.currentTimeMillis() - start
            val ok = !res.text.isNullOrBlank()
            EngineBenchmarkResult(
                engineKey = providerKey,
                success = ok,
                latencyMs = elapsed,
                hitCount = if (ok) 1 else 0,
                summary = if (ok) "متصل ويستجيب خلال ${elapsed}ms" else "استجابة فارغة"
            )
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            val elapsed = System.currentTimeMillis() - start
            EngineBenchmarkResult(
                engineKey = providerKey,
                success = false,
                latencyMs = elapsed,
                hitCount = 0,
                summary = "خطأ: ${e.localizedMessage ?: "فشل الاتصال"}"
            )
        }
    }

    private companion object {
        const val TAG = "GeminiVisionIdentity"
    }
}
