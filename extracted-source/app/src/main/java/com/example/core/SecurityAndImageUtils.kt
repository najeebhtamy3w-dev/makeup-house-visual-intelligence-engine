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
    private const val MAX_ZIP_ENTRIES = 200
    private const val MAX_ZIP_UNCOMPRESSED_BYTES = 80L * 1024L * 1024L // 80 MB
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
        return try {
            val dir = File(context.filesDir, "mhvie_images/$batchFolder").apply { mkdirs() }
            val outFile = File(dir, "orig_${UUID.randomUUID().toString().take(8)}.jpg")
            context.contentResolver.openInputStream(uri)?.use { input ->
                val rawBytes = input.readBytes()
                if (rawBytes.size > MAX_SINGLE_IMAGE_BYTES) return null
                val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                BitmapFactory.decodeByteArray(rawBytes, 0, rawBytes.size, bounds)
                if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null

                val bitmap = decodeScaledBitmapFromBytes(rawBytes, 1400) ?: return null
                FileOutputStream(outFile).use { fos ->
                    bitmap.compress(Bitmap.CompressFormat.JPEG, 90, fos)
                }
                bitmap.recycle()
                outFile.absolutePath
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to copy image uri: $uri", e)
            null
        }
    }

    /**
     * Extracts image files from a ZIP archive with Zip-Slip and Zip-Bomb protections.
     * Groups images in subfolders as belonging to one product, or flat images individually.
     */
    data class ExtractedZipGroup(
        val groupName: String,
        val filePaths: List<String>
    )

    fun safeExtractImagesFromZip(
        context: Context,
        zipUri: Uri,
        batchFolder: String
    ): Result<List<ExtractedZipGroup>> {
        return try {
            val destRoot = File(context.filesDir, "mhvie_images/$batchFolder").apply { mkdirs() }
            val canonicalRoot = destRoot.canonicalPath
            val groupedFiles = linkedMapOf<String, MutableList<String>>()
            var totalBytes = 0L
            var entryCount = 0

            context.contentResolver.openInputStream(zipUri)?.use { rawIn ->
                ZipInputStream(BufferedInputStream(rawIn)).use { zis ->
                    var entry = zis.nextEntry
                    while (entry != null) {
                        entryCount++
                        if (entryCount > MAX_ZIP_ENTRIES) {
                            return Result.failure(IllegalStateException("تجاوز الأرشيف الحد الأقصى للملفات ($MAX_ZIP_ENTRIES)"))
                        }
                        if (!entry.isDirectory) {
                            val name = entry.name.replace('\\', '/')
                            val cleanName = name.substringAfterLast('/')
                            val ext = cleanName.substringAfterLast('.', "").lowercase()
                            if (ext in ALLOWED_IMAGE_EXTENSIONS && !cleanName.startsWith("._") && !name.contains("__MACOSX")) {
                                val groupKey = if (name.contains('/')) {
                                    name.substringBeforeLast('/').substringAfterLast('/').ifBlank { "default" }
                                } else {
                                    cleanName.substringBeforeLast('.')
                                }
                                val outFile = File(destRoot, "zip_${entryCount}_${cleanName.replace(Regex("[^a-zA-Z0-9._-]"), "_")}")
                                val canonicalOut = outFile.canonicalPath
                                if (!canonicalOut.startsWith(canonicalRoot + File.separator)) {
                                    return Result.failure(SecurityException("مسار غير آمن داخل الأرشيف (Zip-Slip): $name"))
                                }
                                val buffer = ByteArray(8192)
                                val baos = java.io.ByteArrayOutputStream()
                                var read = zis.read(buffer)
                                while (read != -1) {
                                    totalBytes += read
                                    if (totalBytes > MAX_ZIP_UNCOMPRESSED_BYTES) {
                                        return Result.failure(IllegalStateException("تجاوز حجم فك الضغط الحد الآمن (80MB Zip-Bomb Guard)"))
                                    }
                                    baos.write(buffer, 0, read)
                                    read = zis.read(buffer)
                                }
                                val bytes = baos.toByteArray()
                                val opts = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                                BitmapFactory.decodeByteArray(bytes, 0, bytes.size, opts)
                                if (opts.outWidth > 0 && opts.outHeight > 0) {
                                    FileOutputStream(outFile).use { it.write(bytes) }
                                    groupedFiles.getOrPut(groupKey) { mutableListOf() }.add(outFile.absolutePath)
                                }
                            }
                        }
                        zis.closeEntry()
                        entry = zis.nextEntry
                    }
                }
            } ?: return Result.failure(IllegalStateException("تعذر قراءة ملف ZIP"))

            val groups = groupedFiles.map { (key, list) -> ExtractedZipGroup(key, list.take(5)) }
            if (groups.isEmpty()) {
                Result.failure(IllegalStateException("لم يتم العثور على صور صالحة داخل ملف ZIP"))
            } else {
                Result.success(groups)
            }
        } catch (e: Exception) {
            Log.e(TAG, "ZIP extraction failed", e)
            Result.failure(e)
        }
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
            val lines = context.contentResolver.openInputStream(uri)?.bufferedReader()?.useLines { seq ->
                seq.take(500).toList()
            } ?: return emptyList()
            if (lines.isEmpty()) return emptyList()
            val startIndex = if (lines.first().contains("brand", ignoreCase = true) ||
                lines.first().contains("sku", ignoreCase = true) ||
                lines.first().contains("الماركة")
            ) 1 else 0

            lines.drop(startIndex).mapNotNull { line ->
                val parts = line.split(',', ';', '\t').map { it.trim().trim('"') }
                if (parts.all { it.isBlank() }) return@mapNotNull null
                CsvProductHint(
                    sku = parts.getOrElse(0) { "" },
                    brand = parts.getOrElse(1) { "" },
                    name = parts.getOrElse(2) { "" },
                    size = parts.getOrElse(3) { "" },
                    shade = parts.getOrElse(4) { "" },
                    barcode = parts.getOrElse(5) { "" }
                )
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed parsing CSV", e)
            emptyList()
        }
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
