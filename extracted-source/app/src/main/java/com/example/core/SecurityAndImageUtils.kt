package com.example.core

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Log
import java.io.BufferedInputStream
import java.io.File
import java.io.FileOutputStream
import java.net.InetAddress
import java.net.URI
import java.util.UUID
import java.util.zip.ZipInputStream
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

object SecurityAndImageUtils {
    private const val TAG = "SecurityAndImageUtils"
    private const val MAX_ZIP_ENTRIES = 10000
    private const val MAX_ZIP_UNCOMPRESSED_BYTES = 500L * 1024L * 1024L // 500 MB
    private const val MAX_SINGLE_IMAGE_BYTES = 15L * 1024L * 1024L // 15 MB

    private val ALLOWED_IMAGE_EXTENSIONS = setOf("jpg", "jpeg", "png", "webp", "bmp")

    /**
     * Strict SSRF protection: Allows only public http/https hosts and rejects
     * loopback, private RFC1918, link-local, and cloud metadata addresses.
     */
    fun isSafeExternalUrl(rawUrl: String): Boolean {
        return try {
            val uri = URI(rawUrl.trim())
            val scheme = uri.scheme?.lowercase() ?: return false
            if (scheme != "https" && scheme != "http") return false
            val host = uri.host?.lowercase()?.trim() ?: return false
            if (host.isBlank() || host == "localhost" || host.endsWith(".local") || host.endsWith(".internal")) {
                return false
            }
            if (host == "169.254.169.254" || host == "metadata.google.internal") return false
            val addresses = InetAddress.getAllByName(host)
            for (addr in addresses) {
                if (addr.isAnyLocalAddress ||
                    addr.isLoopbackAddress ||
                    addr.isLinkLocalAddress ||
                    addr.isSiteLocalAddress ||
                    addr.isMulticastAddress
                ) {
                    return false
                }
                val bytes = addr.address
                if (bytes.size == 4) {
                    val b0 = bytes[0].toInt() and 0xFF
                    val b1 = bytes[1].toInt() and 0xFF
                    // Block 100.64.0.0/10 (CGNAT) & 0.0.0.0/8
                    if (b0 == 0 || (b0 == 100 && b1 in 64..127)) return false
                }
            }
            true
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Copies a selected Content Uri into app-private storage safely without requiring
     * READ_EXTERNAL_STORAGE / READ_MEDIA_IMAGES permissions.
     */
    fun copyUriToInternalImageFile(context: Context, uri: Uri, batchFolder: String): String? {
        require(batchFolder.matches(Regex("[a-zA-Z0-9_-]{1,100}")))
        val dir = File(context.filesDir, "mhvie_images/$batchFolder").apply { mkdirs() }
        val temporary = File(dir, "orig_${UUID.randomUUID()}.part")
        return try {
            val input = context.contentResolver.openInputStream(uri) ?: return null
            input.use { source ->
                temporary.outputStream().use { output ->
                    val chunk = ByteArray(8192); var total = 0L
                    while (true) {
                        val count = source.read(chunk); if (count == -1) break
                        total += count; require(total <= MAX_SINGLE_IMAGE_BYTES) { "IMAGE_SIZE_LIMIT" }
                        output.write(chunk, 0, count)
                    }
                }
            }
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeFile(temporary.absolutePath, bounds)
            require(bounds.outWidth > 0 && bounds.outHeight > 0 && bounds.outWidth.toLong() * bounds.outHeight <= 80_000_000) { "INVALID_IMAGE" }
            val extension = when (bounds.outMimeType) { "image/jpeg" -> "jpg"; "image/png" -> "png"; "image/webp" -> "webp"; "image/bmp" -> "bmp"; else -> error("UNSUPPORTED_IMAGE_TYPE") }
            val original = File(dir, temporary.name.removeSuffix(".part") + ".$extension")
            check(temporary.renameTo(original)); original.absolutePath
        } catch (e: Exception) { temporary.delete(); null }
    }

    /**
     * Extracts image files from a ZIP archive with Zip-Slip and Zip-Bomb protections.
     * Groups images in subfolders as belonging to one product, or flat images individually.
     */
    data class ExtractedZipGroup(
        val groupName: String,
        val filePaths: List<String>
    )

    fun safeExtractImagesFromZip(context: Context, zipUri: Uri, batchFolder: String): Result<List<ExtractedZipGroup>> {
        require(batchFolder.matches(Regex("[a-zA-Z0-9_-]{1,100}")))
        val destination = File(context.filesDir, "mhvie_images/$batchFolder").apply { mkdirs() }
        val created = mutableListOf<File>()
        return runCatching {
            val groups = linkedMapOf<String, MutableList<String>>()
            var total = 0L; var count = 0
            val raw = context.contentResolver.openInputStream(zipUri) ?: error("تعذر قراءة ZIP")
            ZipInputStream(BufferedInputStream(raw)).use { zip ->
                while (true) {
                    val entry = zip.nextEntry ?: break
                    require(++count <= MAX_ZIP_ENTRIES) { "ZIP_ENTRY_LIMIT" }
                    val name = entry.name.replace('\\', '/')
                    val leaf = name.substringAfterLast('/')
                    val ext = leaf.substringAfterLast('.', "").lowercase()
                    val accepted = !entry.isDirectory && ext in ALLOWED_IMAGE_EXTENSIONS && !leaf.startsWith("._") && !name.contains("__MACOSX")
                    val output = if (accepted) File(destination, "zip_${UUID.randomUUID()}.$ext").also { created.add(it) } else null
                    val stream = output?.outputStream()
                    try {
                        var entryBytes = 0L; val buffer = ByteArray(8192)
                        while (true) {
                            val n = zip.read(buffer); if (n == -1) break
                            total += n; entryBytes += n
                            require(total <= MAX_ZIP_UNCOMPRESSED_BYTES && entryBytes <= MAX_SINGLE_IMAGE_BYTES) { "ZIP_SIZE_LIMIT" }
                            stream?.write(buffer, 0, n)
                        }
                    } finally { stream?.close() }
                    if (output != null) {
                        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                        BitmapFactory.decodeFile(output.absolutePath, bounds)
                        require(bounds.outWidth > 0 && bounds.outHeight > 0 && bounds.outWidth.toLong() * bounds.outHeight <= 80_000_000) { "INVALID_ZIP_IMAGE" }
                        val group = if (name.contains('/')) name.substringBeforeLast('/') else leaf.substringBeforeLast('.')
                        groups.getOrPut(group) { mutableListOf() }.add(output.absolutePath)
                    }
                    zip.closeEntry()
                }
            }
            require(groups.isNotEmpty()) { "لم توجد صور صالحة داخل ZIP" }
            groups.map { (name, paths) -> ExtractedZipGroup(name, paths) }
        }.onFailure { created.forEach(File::delete) }
    }

    /**
     * Parses optional CSV / Excel-exported CSV product rows:
     * Expected columns (flexible header): sku, brand, name, size, shade, barcode
     */
    data class CsvProductHint(
        val sku: String,
        val brand: String,
        val name: String,
        val size: String,
        val shade: String,
        val barcode: String
    )

    fun parseCsvProductHints(context: Context, uri: Uri): List<CsvProductHint> {
        return try {
            val bytes = context.contentResolver.openInputStream(uri)?.use { stream ->
                val out = java.io.ByteArrayOutputStream(); val buffer = ByteArray(8192)
                while (true) { val n = stream.read(buffer); if (n == -1) break; require(out.size() + n <= 10_000_000) { "CSV_SIZE_LIMIT" }; out.write(buffer, 0, n) }
                out.toByteArray()
            } ?: return emptyList()
            parseCsvProductHintText(bytes.toString(Charsets.UTF_8))
        } catch (e: Exception) {
            Log.e(TAG, "Failed parsing CSV", e)
            emptyList()
        }
    }

    /** Bounded CSV parsing without silent row truncation or splitting quoted names. */
    internal fun parseCsvProductHintText(input: String): List<CsvProductHint> {
        require(input.length <= 10_000_000) { "CSV_SIZE_LIMIT" }
        val text = input.removePrefix("\uFEFF")
        val counts = mutableMapOf(',' to 0, ';' to 0, '\t' to 0)
        var quoted = false; var index = 0
        while (index < text.length) {
            val c = text[index]
            if (c == '"') { if (quoted && text.getOrNull(index + 1) == '"') index++ else quoted = !quoted }
            else if (!quoted && c in counts) counts[c] = counts.getValue(c) + 1
            else if (!quoted && c in "\r\n") break
            index++
        }
        val delimiter = counts.maxBy { it.value }.key
        val rows = mutableListOf<List<String>>(); var fields = mutableListOf<String>(); val cell = StringBuilder()
        quoted = false; index = 0
        fun finishCell() { require(fields.size < 64) { "CSV_COLUMN_LIMIT" }; fields.add(cell.toString()); cell.setLength(0) }
        fun finishRow() { finishCell(); if (fields.any { it.isNotBlank() }) { require(rows.size < 20_001) { "CSV_ROW_LIMIT" }; rows.add(fields.toList()) }; fields = mutableListOf() }
        while (index < text.length) {
            val c = text[index]
            when {
                c == '"' && quoted && text.getOrNull(index + 1) == '"' -> { cell.append('"'); index++ }
                c == '"' -> { require(quoted || cell.isEmpty()) { "INVALID_CSV_QUOTE" }; quoted = !quoted }
                !quoted && c == delimiter -> finishCell()
                !quoted && c in "\r\n" -> { finishRow(); if (c == '\r' && text.getOrNull(index + 1) == '\n') index++ }
                else -> { require(cell.length < 4096) { "CSV_CELL_LIMIT" }; cell.append(c) }
            }
            index++
        }
        require(!quoted) { "UNCLOSED_CSV_QUOTE" }
        if (cell.isNotEmpty() || fields.isNotEmpty()) finishRow()
        val header = rows.firstOrNull().orEmpty().map { it.trim().lowercase() }
        val start = if (header.any { it in setOf("sku", "brand", "الماركة", "barcode", "الباركود") }) 1 else 0
        require(rows.size - start <= 20_000) { "CSV_ROW_LIMIT" }
        return rows.drop(start).map { p -> CsvProductHint(p.getOrElse(0) { "" }, p.getOrElse(1) { "" }, p.getOrElse(2) { "" }, p.getOrElse(3) { "" }, p.getOrElse(4) { "" }, p.getOrElse(5) { "" }) }
    }

    fun decodeScaledBitmapFromFile(path: String, maxDimension: Int = 1024): Bitmap? {
        return try {
            val file = File(path)
            if (!file.exists()) return null
            val opts = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeFile(path, opts)
            val sample = calculateInSampleSize(opts.outWidth, opts.outHeight, maxDimension)
            val decodeOpts = BitmapFactory.Options().apply {
                inSampleSize = sample
                inPreferredConfig = Bitmap.Config.ARGB_8888
            }
            BitmapFactory.decodeFile(path, decodeOpts)
        } catch (e: Exception) {
            null
        }
    }

    fun decodeScaledBitmapFromBytes(bytes: ByteArray, maxDimension: Int = 1024): Bitmap? {
        return try {
            val opts = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size, opts)
            val sample = calculateInSampleSize(opts.outWidth, opts.outHeight, maxDimension)
            val decodeOpts = BitmapFactory.Options().apply {
                inSampleSize = sample
                inPreferredConfig = Bitmap.Config.ARGB_8888
            }
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size, decodeOpts)
        } catch (e: Exception) {
            null
        }
    }

    private fun calculateInSampleSize(width: Int, height: Int, maxDim: Int): Int {
        var inSampleSize = 1
        val largest = max(width, height)
        if (largest > maxDim) {
            while ((largest / inSampleSize) > maxDim) {
                inSampleSize *= 2
            }
        }
        return max(1, inSampleSize)
    }

    /**
     * Computes 64-bit Difference Hash (dHash) for fast perceptual deduplication.
     */
    fun computeDHash(bitmap: Bitmap): String {
        val scaled = Bitmap.createScaledBitmap(bitmap, 9, 8, true)
        var hash = 0UL
        var bit = 0
        for (y in 0 until 8) {
            for (x in 0 until 8) {
                val left = luminance(scaled.getPixel(x, y))
                val right = luminance(scaled.getPixel(x + 1, y))
                if (left > right) {
                    hash = hash or (1UL shl bit)
                }
                bit++
            }
        }
        if (scaled != bitmap) scaled.recycle()
        return hash.toString(16).padStart(16, '0')
    }

    fun hammingDistance(hex1: String, hex2: String): Int {
        if (hex1.isBlank() || hex2.isBlank()) return 64
        return try {
            val v1 = hex1.toULong(16)
            val v2 = hex2.toULong(16)
            (v1 xor v2).countOneBits()
        } catch (_: Exception) {
            64
        }
    }

    /**
     * Deterministic technical image quality assessment (resolution, sharpness, lighting balance).
     */
    data class TechnicalQualityMetrics(
        val width: Int,
        val height: Int,
        val sharpnessScore: Double,
        val exposureScore: Double,
        val resolutionScore: Double
    )

    fun evaluateTechnicalQuality(bitmap: Bitmap): TechnicalQualityMetrics {
        val w = bitmap.width
        val h = bitmap.height
        val minDim = min(w, h)
        val resScore = when {
            minDim >= 1000 -> 1.0
            minDim >= 700 -> 0.85
            minDim >= 450 -> 0.65
            minDim >= 250 -> 0.40
            else -> 0.20
        }

        val sample = Bitmap.createScaledBitmap(bitmap, 64, 64, true)
        var sumLaplacian = 0.0
        var sumLum = 0.0
        var count = 0
        for (y in 1 until 63) {
            for (x in 1 until 63) {
                val c = luminance(sample.getPixel(x, y))
                val l = luminance(sample.getPixel(x - 1, y))
                val r = luminance(sample.getPixel(x + 1, y))
                val u = luminance(sample.getPixel(x, y - 1))
                val d = luminance(sample.getPixel(x, y + 1))
                val lap = abs(4 * c - l - r - u - d)
                sumLaplacian += lap
                sumLum += c
                count++
            }
        }
        if (sample != bitmap) sample.recycle()

        val meanLap = if (count > 0) sumLaplacian / count else 0.0
        val meanLum = if (count > 0) sumLum / count else 128.0
        val sharpness = (meanLap / 45.0).coerceIn(0.1, 1.0)
        // Ideal mean luminance around 110..200 for clean studio/commercial product images
        val exposure = (1.0 - abs(meanLum - 150.0) / 150.0).coerceIn(0.2, 1.0)

        return TechnicalQualityMetrics(
            width = w,
            height = h,
            sharpnessScore = sharpness,
            exposureScore = exposure,
            resolutionScore = resScore
        )
    }

    private fun luminance(pixel: Int): Double {
        val r = (pixel shr 16) and 0xFF
        val g = (pixel shr 8) and 0xFF
        val b = pixel and 0xFF
        return 0.299 * r + 0.587 * g + 0.114 * b
    }
}
