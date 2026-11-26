package com.example.engine

import android.graphics.Bitmap
import android.graphics.Matrix
import com.google.zxing.BarcodeFormat
import com.google.zxing.BinaryBitmap
import com.google.zxing.DecodeHintType
import com.google.zxing.MultiFormatReader
import com.google.zxing.RGBLuminanceSource
import com.google.zxing.common.HybridBinarizer

class ZXingBarcodeProvider : BarcodeProvider {
    override val providerKey: String = "zxing_barcode"

    private val reader = MultiFormatReader().apply {
        setHints(
            mapOf(
                DecodeHintType.TRY_HARDER to true,
                DecodeHintType.POSSIBLE_FORMATS to listOf(
                    BarcodeFormat.EAN_13,
                    BarcodeFormat.EAN_8,
                    BarcodeFormat.UPC_A,
                    BarcodeFormat.UPC_E,
                    BarcodeFormat.CODE_128,
                    BarcodeFormat.CODE_39,
                    BarcodeFormat.QR_CODE
                )
            )
        )
    }

    override fun decodeBarcode(bitmaps: List<Bitmap>): String {
        for (bmp in bitmaps) {
            decodeSingleOrientation(bmp)?.let { return it }
            // Try 90-degree rotated orientation for vertical barcodes on cosmetic bottles
            val matrix = Matrix().apply { postRotate(90f) }
            val rotated = Bitmap.createBitmap(bmp, 0, 0, bmp.width, bmp.height, matrix, true)
            val result = decodeSingleOrientation(rotated)
            if (rotated != bmp) rotated.recycle()
            if (result != null) return result
        }
        return ""
    }

    private fun decodeSingleOrientation(bitmap: Bitmap): String? {
        return try {
            val w = bitmap.width
            val h = bitmap.height
            val pixels = IntArray(w * h)
            bitmap.getPixels(pixels, 0, w, 0, 0, w, h)
            val source = RGBLuminanceSource(w, h, pixels)
            val binary = BinaryBitmap(HybridBinarizer(source))
            reader.decodeWithState(binary).text?.trim()?.takeIf { it.isNotBlank() }
        } catch (_: Exception) {
            null
        } finally {
            reader.reset()
        }
    }
}
