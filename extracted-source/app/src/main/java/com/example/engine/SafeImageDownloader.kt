package com.example.engine

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log
import com.example.core.SecurityAndImageUtils
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.util.UUID

data class DownloadedImageResult(
    val bitmap: Bitmap,
    val localPath: String?,
    val widthPx: Int,
    val heightPx: Int,
    val dHash: String
)

class SafeImageDownloader(private val context: Context) {
    private val maxDownloadBytes = 15L * 1024L * 1024L

    suspend fun downloadAndValidate(
        imageUrl: String,
        productId: String,
        saveLocally: Boolean = false
    ): Result<DownloadedImageResult> = withContext(Dispatchers.IO) {
        if (!SecurityAndImageUtils.isSafeExternalUrl(imageUrl)) {
            return@withContext Result.failure(SecurityException("تم حظر الرابط لاعتبارات أمان SSRF: $imageUrl"))
        }
        try {
            val req = Request.Builder()
                .url(imageUrl)
                .header("User-Agent", "MakeupHouseVisualIntelligence/1.0")
                .build()
            SharedHttpClient.client.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) {
                    return@withContext Result.failure(IllegalStateException("فشل التنزيل HTTP ${resp.code}"))
                }
                val contentType = resp.header("Content-Type").orEmpty().lowercase()
                if (contentType.isNotBlank() && !contentType.startsWith("image/")) {
                    return@withContext Result.failure(IllegalArgumentException("الملف ليس صورة صالحة ($contentType)"))
                }
                val contentLen = resp.body?.contentLength() ?: -1L
                if (contentLen > maxDownloadBytes) {
                    return@withContext Result.failure(IllegalStateException("حجم الصورة يتجاوز الحد الآمن (15MB)"))
                }
                val bytes = resp.body?.bytes() ?: return@withContext Result.failure(IllegalStateException("بيانات فارغة"))
                if (bytes.size > maxDownloadBytes) {
                    return@withContext Result.failure(IllegalStateException("حجم الصورة يتجاوز الحد الآمن"))
                }

                val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
                if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
                    return@withContext Result.failure(IllegalArgumentException("فشل فك تشفير الصورة"))
                }

                val scaled = SecurityAndImageUtils.decodeScaledBitmapFromBytes(bytes, 1024)
                    ?: return@withContext Result.failure(IllegalStateException("تعذر معالجة أبعاد الصورة"))
                val dHash = SecurityAndImageUtils.computeDHash(scaled)

                val savedPath = if (saveLocally) {
                    val dir = File(context.filesDir, "mhvie_images/downloaded/$productId").apply { mkdirs() }
                    val target = File(dir, "cand_${UUID.randomUUID().toString().take(8)}.jpg")
                    val tmp = File(dir, ".tmp_${target.name}")
                    FileOutputStream(tmp).use { it.write(bytes) }
                    if (tmp.renameTo(target)) target.absolutePath else null
                } else null

                Result.success(
                    DownloadedImageResult(
                        bitmap = scaled,
                        localPath = savedPath,
                        widthPx = bounds.outWidth,
                        heightPx = bounds.outHeight,
                        dHash = dHash
                    )
                )
            }
        } catch (e: Exception) {
            Log.w(TAG, "Download failed for $imageUrl: ${e.message}")
            Result.failure(e)
        }
    }

    private companion object {
        const val TAG = "SafeImageDownloader"
    }
}
