package com.example

import com.example.core.SecurityAndImageUtils
import org.junit.Assert.*
import org.junit.Test

class MhvieCoreUnitTest {
    @Test fun sixThousandRowsAreNotSilentlyTruncated() {
        val text = "sku,brand,name,size,shade,barcode\n" + (1..6000).joinToString("\n") { "$it,QV,Wash $it,30ml,,123" }
        val result = SecurityAndImageUtils.parseCsvProductHintText(text)
        assertEquals(6000, result.size); assertEquals("6000", result.last().sku); assertEquals("Wash 6000", result.last().name)
    }
    @Test fun quotesCommasAndEmbeddedNewlinesRemainProductText() {
        val text = "sku,brand,name,size,shade,barcode\n1,QV,\"Gentle, \"\"Daily\"\"\nWash\",1l,,123\n"
        val row = SecurityAndImageUtils.parseCsvProductHintText(text).single()
        assertEquals("Gentle, \"Daily\"\nWash", row.name); assertEquals("1l", row.size)
    }
    @Test fun malformedQuotesAreRejectedAndDelimitedFieldsRemainSeparate() {
        assertTrue(runCatching { SecurityAndImageUtils.parseCsvProductHintText("1,QV,\"bad") }.isFailure)
        val row = SecurityAndImageUtils.parseCsvProductHintText("sku;brand;name;size;shade;barcode\n1;QV;Wash;1l;;123").single()
        assertEquals("QV", row.brand); assertEquals("123", row.barcode)
    }
}
