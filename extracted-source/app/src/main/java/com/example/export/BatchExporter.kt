package com.example.export

import android.content.Context
import android.content.Intent
import androidx.core.content.FileProvider
import com.example.model.BatchJob
import com.example.model.BrandProfile
import com.example.model.DiscoveredImage
import com.example.model.ProductRecord
import com.example.model.ProductStatus
import com.squareup.moshi.Moshi
import java.io.BufferedOutputStream
import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

object BatchExporter {
    private val mapJsonAdapter by lazy {
        Moshi.Builder().build().adapter(Map::class.java).indent("  ")
    }

    private fun exportDir(context: Context): File =
        File(context.cacheDir, "exports").apply { mkdirs() }

    fun shareFile(context: Context, file: File, mimeType: String, titleAr: String) {
        val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = mimeType
            putExtra(Intent.EXTRA_STREAM, uri)
            putExtra(Intent.EXTRA_SUBJECT, titleAr)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(Intent.createChooser(intent, titleAr).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    fun exportCsvExcel(
        context: Context,
        batch: BatchJob,
        products: List<ProductRecord>,
        candidatesByProduct: Map<String, List<DiscoveredImage>>
    ): File = exportCsvExcelToDir(exportDir(context), batch, products, candidatesByProduct)

    internal fun exportCsvExcelToDir(
        dir: File,
        batch: BatchJob,
        products: List<ProductRecord>,
        candidatesByProduct: Map<String, List<DiscoveredImage>>
    ): File {
        dir.mkdirs()
        val file = File(dir, "MH_VIE_${batch.id}_REPORT.csv")
        val sb = StringBuilder()
        // UTF-8 BOM so Microsoft Excel renders Arabic cleanly
        sb.append('\uFEFF')
        sb.appendLine(
            "رقم المنتج,اسم المنتج,الماركة,الحجم,الدرجة,الباركود,حالة البحث,عدد الصور المكتشفة,عدد الصور المطابقة,روابط الصور,روابط المصادر,درجة المطابقة,درجة الجودة,حالة حقوق الاستخدام,سبب عدم العثور,حالة الاعتماد"
        )
        for (p in products) {
            val cands = candidatesByProduct[p.id].orEmpty()
            val topMatch = cands.maxOfOrNull { it.matchScore } ?: 0.0
            val topAesthetic = cands.maxOfOrNull { it.aestheticScore } ?: 0.0
            val imgUrls = cands.take(5).joinToString(" | ") { it.imageUrl }
            val pageUrls = cands.take(5).joinToString(" | ") { it.pageUrl.ifBlank { it.sourceName } }
            val rights = cands.firstOrNull()?.rightsEnum()?.labelAr ?: "غير محدد"
            val row = listOf(
                p.id,
                p.displayTitle(),
                p.brand,
                p.sizeWeight,
                p.shadeColor,
                p.barcode,
                p.statusEnum().labelAr,
                p.discoveredCount.toString(),
                p.matchedCount.toString(),
                imgUrls,
                pageUrls,
                "%.2f".format(topMatch),
                "%.2f".format(topAesthetic),
                rights,
                p.zeroReasonEnum().labelAr,
                p.approvalEnum().labelAr
            ).joinToString(",") { cell -> "\"${safeCsvCell(cell).replace("\"", "\"\"")}\"" }
            sb.appendLine(row)
        }
        file.writeText(sb.toString(), Charsets.UTF_8)
        return file
    }

    fun exportHtmlGallery(
        context: Context,
        batch: BatchJob,
        products: List<ProductRecord>,
        candidatesByProduct: Map<String, List<DiscoveredImage>>
    ): File = exportHtmlGalleryToDir(exportDir(context), batch, products, candidatesByProduct)

    internal fun exportHtmlGalleryToDir(
        dir: File,
        batch: BatchJob,
        products: List<ProductRecord>,
        candidatesByProduct: Map<String, List<DiscoveredImage>>
    ): File {
        dir.mkdirs()
        val file = File(dir, "MH_VIE_${batch.id}_GALLERY.html")
        val cardsHtml = buildString {
            for (p in products) {
                val cands = candidatesByProduct[p.id].orEmpty()
                append("<div class='card'>")
                append("<h2>${escapeHtml(p.displayTitle())}</h2>")
                append("<p class='meta'>الماركة: ${escapeHtml(p.brand)} | الحجم: ${escapeHtml(p.sizeWeight)} | الباركود: ${escapeHtml(p.barcode)} | الحالة: <strong>${escapeHtml(p.statusEnum().labelAr)}</strong></p>")
                if (cands.isEmpty()) {
                    append("<p class='zero'>لا توجد صور: ${escapeHtml(p.zeroReasonEnum().labelAr)}</p>")
                } else {
                    append("<div class='grid'>")
                    for (c in cands.take(6)) {
                        append("<div class='thumb'>")
                        append("<img src='${escapeHtml(safeWebUrl(c.imageUrl))}' alt='${escapeHtml(p.displayTitle())}' loading='lazy'/>")
                        append("<div class='caption'>")
                        append("<span>تطابق: ${(c.matchScore * 100).toInt()}% | جودة: ${(c.aestheticScore * 100).toInt()}%</span><br/>")
                        append("<span>${escapeHtml(c.rightsEnum().labelAr)}</span><br/>")
                        append("<a href='${escapeHtml(safeWebUrl(c.pageUrl.ifBlank { c.imageUrl }))}' target='_blank'>المصدر: ${escapeHtml(c.sourceName)}</a>")
                        append("</div></div>")
                    }
                    append("</div>")
                }
                append("</div>")
            }
        }
        val html = """
            <!DOCTYPE html>
            <html lang="ar" dir="rtl">
            <head>
              <meta charset="utf-8"/>
              <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src https: data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"/>
              <meta name="viewport" content="width=device-width,initial-scale=1"/>
              <title>معرض نتائج ${escapeHtml(batch.title)} — MAKEUP HOUSE</title>
              <style>
                body{font-family:system-ui,-apple-system,sans-serif;background:#FCF8F6;color:#201A1B;margin:0;padding:24px;}
                header{background:#1A1318;color:#FAF6F2;padding:20px 24px;border-radius:16px;margin-bottom:24px;}
                .card{background:#fff;border:1px solid #F3E4E6;border-radius:16px;padding:18px;margin-bottom:18px;}
                .meta{color:#524346;font-size:14px;}
                .zero{color:#BA1A1A;font-weight:bold;}
                .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;margin-top:12px;}
                .thumb{border:1px solid #eee;border-radius:12px;overflow:hidden;background:#fafafa;}
                .thumb img{width:100%;height:180px;object-fit:contain;background:#fff;}
                .caption{padding:8px 10px;font-size:12px;line-height:1.5;}
                a{color:#A82C51;}
              </style>
            </head>
            <body>
              <header>
                <h1>MAKEUP HOUSE VISUAL INTELLIGENCE ENGINE</h1>
                <p>الدفعة: ${escapeHtml(batch.title)} | إجمالي المنتجات: ${products.size}</p>
              </header>
              $cardsHtml
            </body>
            </html>
        """.trimIndent()
        file.writeText(html, Charsets.UTF_8)
        return file
    }

    fun exportBatchJson(
        context: Context,
        batch: BatchJob,
        products: List<ProductRecord>,
        candidatesByProduct: Map<String, List<DiscoveredImage>>
    ): File {
        val file = File(exportDir(context), "MH_VIE_${batch.id}_MANIFEST.json")
        file.writeText(buildManifestJson(batch, products, candidatesByProduct), Charsets.UTF_8)
        return file
    }

    fun exportBatchZip(
        context: Context,
        batch: BatchJob,
        products: List<ProductRecord>,
        candidatesByProduct: Map<String, List<DiscoveredImage>>
    ): File = exportBatchZipToDir(exportDir(context), batch, products, candidatesByProduct)

    internal fun exportBatchZipToDir(
        dir: File,
        batch: BatchJob,
        products: List<ProductRecord>,
        candidatesByProduct: Map<String, List<DiscoveredImage>>
    ): File {
        dir.mkdirs()
        val rootName = "MAKEUP_HOUSE_BATCH_${batch.id}"
        val zipFile = File(dir, "$rootName.zip")
        val csvFile = exportCsvExcelToDir(dir, batch, products, candidatesByProduct)
        val htmlFile = exportHtmlGalleryToDir(dir, batch, products, candidatesByProduct)
        val manifestStr = buildManifestJson(batch, products, candidatesByProduct)

        ZipOutputStream(BufferedOutputStream(FileOutputStream(zipFile))).use { zos ->
            fun addTextEntry(path: String, text: String) {
                zos.putNextEntry(ZipEntry("$rootName/$path"))
                zos.write(text.toByteArray(Charsets.UTF_8))
                zos.closeEntry()
            }

            addTextEntry("MANIFEST.json", manifestStr)
            addTextEntry("REPORTS/report.csv", csvFile.readText(Charsets.UTF_8))
            addTextEntry("REPORTS/gallery.html", htmlFile.readText(Charsets.UTF_8))

            for (p in products) {
                val folder = when (p.statusEnum()) {
                    ProductStatus.FOUND -> "FOUND_PRODUCTS"
                    ProductStatus.REVIEW_REQUIRED -> "REVIEW_REQUIRED"
                    else -> "ZERO_RESULTS"
                }
                val cands = candidatesByProduct[p.id].orEmpty()
                val prodJson = mapJsonAdapter.toJson(
                    mapOf(
                        "id" to p.id,
                        "title" to p.displayTitle(),
                        "brand" to p.brand,
                        "productNameEn" to p.productNameEn,
                        "productNameAr" to p.productNameAr,
                        "sizeWeight" to p.sizeWeight,
                        "shadeColor" to p.shadeColor,
                        "barcode" to p.barcode,
                        "status" to p.status,
                        "zeroResultReason" to p.zeroResultReason,
                        "approvalStatus" to p.approvalStatus,
                        "candidates" to cands.map { c ->
                            mapOf(
                                "imageUrl" to c.imageUrl,
                                "pageUrl" to c.pageUrl,
                                "sourceName" to c.sourceName,
                                "rightsStatus" to c.rightsStatus,
                                "matchScore" to c.matchScore,
                                "aestheticScore" to c.aestheticScore,
                                "reviewDecision" to c.reviewDecision,
                                "sha256" to c.perceptualHash,
                                "licenseName" to c.licenseName,
                                "verificationNotes" to c.verificationNotes
                            )
                        }
                    )
                )
                addTextEntry("$folder/${p.id}/product.json", prodJson)

                // Include original store image if available locally
                p.localOriginalPaths.forEachIndexed { idx, path ->
                    val f = File(path)
                    if (f.isFile) {
                        zos.putNextEntry(ZipEntry("$rootName/ORIGINAL_IMAGES/${p.id}_orig_$idx.${imageExtension(f)}"))
                        f.inputStream().use { it.copyTo(zos) }
                        zos.closeEntry()
                    }
                }
                // Include locally downloaded candidate images if saved
                cands.forEachIndexed { idx, c ->
                    if (c.localSavedPath.isNotBlank()) {
                        val f = File(c.localSavedPath)
                        if (f.isFile) {
                            zos.putNextEntry(ZipEntry("$rootName/$folder/${p.id}/candidate_$idx.${imageExtension(f)}"))
                            f.inputStream().use { it.copyTo(zos) }
                            zos.closeEntry()
                        }
                    }
                }
            }
        }
        return zipFile
    }

    fun exportKnowledgeBaseBackup(
        context: Context,
        brands: List<BrandProfile>,
        products: List<ProductRecord>
    ): File {
        val dir = File(context.filesDir, "backups").apply { mkdirs() }
        val file = File(dir, "MH_VIE_KNOWLEDGE_BACKUP.json")
        val root = mapOf(
            "version" to "1.0",
            "exportedAtMillis" to System.currentTimeMillis(),
            "brands" to brands.map { b ->
                mapOf(
                    "brandName" to b.brandName,
                    "officialWebsite" to b.officialWebsite,
                    "instagramHandle" to b.instagramHandle,
                    "pinterestHandle" to b.pinterestHandle,
                    "trustedDomains" to b.trustedDomains,
                    "successfulQueries" to b.successfulQueries,
                    "processedCount" to b.processedCount,
                    "successRate" to b.successRate
                )
            },
            "productsCount" to products.size
        )
        file.writeText(mapJsonAdapter.toJson(root), Charsets.UTF_8)
        return file
    }

    private fun buildManifestJson(
        batch: BatchJob,
        products: List<ProductRecord>,
        candidatesByProduct: Map<String, List<DiscoveredImage>>
    ): String {
        val root = mapOf(
            "batchId" to batch.id,
            "title" to batch.title,
            "status" to batch.status,
            "strategy" to batch.strategy,
            "totalProducts" to products.size,
            "products" to products.map { p ->
                val cands = candidatesByProduct[p.id].orEmpty()
                mapOf(
                    "id" to p.id,
                    "brand" to p.brand,
                    "productNameEn" to p.productNameEn,
                    "productNameAr" to p.productNameAr,
                    "sizeWeight" to p.sizeWeight,
                    "shadeColor" to p.shadeColor,
                    "barcode" to p.barcode,
                    "status" to p.status,
                    "zeroResultReason" to p.zeroResultReason,
                    "approvalStatus" to p.approvalStatus,
                    "candidatesCount" to cands.size,
                    "publicationAllowed" to false,
                    "sourcesAndRights" to cands.map { c -> mapOf("sourceUrl" to c.pageUrl, "imageUrl" to c.imageUrl, "sourceName" to c.sourceName, "rightsStatus" to c.rightsStatus, "license" to c.licenseName, "reviewDecision" to c.reviewDecision, "sha256" to c.perceptualHash, "verificationNotes" to c.verificationNotes) },
                    "bestImageUrl" to p.bestImageUrl
                )
            }
        )
        return mapJsonAdapter.toJson(root)
    }

    private fun imageExtension(file: File): String {
        val options = android.graphics.BitmapFactory.Options().apply { inJustDecodeBounds = true }
        android.graphics.BitmapFactory.decodeFile(file.absolutePath, options)
        return when (options.outMimeType) { "image/png" -> "png"; "image/webp" -> "webp"; "image/jpeg" -> "jpg"; "image/bmp" -> "bmp"; else -> "bin" }
    }

    internal fun safeCsvCell(value: String): String = if (value.trimStart().firstOrNull() in setOf('=', '+', '-', '@', '\t', '\r')) "'" + value else value

    private fun safeWebUrl(value: String): String = runCatching {
        val uri = java.net.URI(value)
        if (uri.scheme == "https" && !uri.host.isNullOrBlank() && uri.userInfo == null) value else ""
    }.getOrDefault("")

    private fun escapeHtml(input: String): String =
        input.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\"", "&quot;")
            .replace("'", "&#39;")
}
