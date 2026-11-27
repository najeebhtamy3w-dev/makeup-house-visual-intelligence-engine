package com.example

import android.content.Context
import android.graphics.Bitmap
import android.net.Uri
import androidx.test.core.app.ApplicationProvider
import com.example.core.SecurityAndImageUtils
import com.example.data.BackendGateway
import com.example.data.LocalWorkspace
import com.example.data.RemoteLink
import com.example.model.*
import com.google.firebase.Timestamp
import org.junit.Assert.*
import org.junit.Before
import org.junit.After
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import java.util.Date
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class MhvieRobolectricTest {
    private lateinit var context: Context
    @Before fun prepare() { context = ApplicationProvider.getApplicationContext(); context.deleteDatabase("mhvie_workspace.sqlite"); context.getSharedPreferences("mhvie_backend", 0).edit().clear().commit() }
    @After fun clean() { context.deleteDatabase("mhvie_workspace.sqlite") }
    private fun png(): ByteArray {
        val image = java.awt.image.BufferedImage(32, 20, java.awt.image.BufferedImage.TYPE_INT_ARGB)
        return java.io.ByteArrayOutputStream().use { output ->
            check(javax.imageio.ImageIO.write(image, "png", output)); output.toByteArray()
        }
    }
    @Test fun originalImageBytesAndFormatArePreserved() {
        val source = File(context.cacheDir, "source.png").apply { writeBytes(png()) }
        val result = SecurityAndImageUtils.copyUriToInternalImageFile(context, Uri.fromFile(source), "test-original")
        assertNotNull(result); assertTrue(result!!.endsWith(".png")); assertArrayEquals(source.readBytes(), File(result).readBytes())
        val bounds = android.graphics.BitmapFactory.Options().apply { inJustDecodeBounds = true }
        android.graphics.BitmapFactory.decodeFile(result, bounds)
        assertEquals(32, bounds.outWidth); assertEquals(20, bounds.outHeight)
    }
    @Test fun invalidImageDoesNotBecomeProductPhoto() {
        val source = File(context.cacheDir, "fake.jpg").apply { writeText("not an image") }
        assertNull(SecurityAndImageUtils.copyUriToInternalImageFile(context, Uri.fromFile(source), "test-invalid"))
    }
    @Test fun zipTraversalCannotEscapeAndSevenImagesAreNotTruncated() {
        val source = File(context.cacheDir, "products.zip")
        ZipOutputStream(source.outputStream()).use { zip ->
            repeat(7) { i -> zip.putNextEntry(ZipEntry("../../product/photo$i.png")); zip.write(png()); zip.closeEntry() }
        }
        val groups = SecurityAndImageUtils.safeExtractImagesFromZip(context, Uri.fromFile(source), "test-zip").getOrThrow()
        assertEquals(1, groups.size); assertEquals(7, groups.single().filePaths.size)
        val root = File(context.filesDir, "mhvie_images/test-zip").canonicalFile
        groups.single().filePaths.forEach { assertEquals(root, File(it).canonicalFile.parentFile) }
    }
    @Test fun ignoredZipEntryIsAlsoBounded() {
        val source = File(context.cacheDir, "metadata-bomb.zip")
        ZipOutputStream(source.outputStream()).use { zip ->
            zip.putNextEntry(ZipEntry("unrelated.txt")); val block = ByteArray(1024 * 1024); repeat(16) { zip.write(block) }; zip.closeEntry()
        }
        assertTrue(SecurityAndImageUtils.safeExtractImagesFromZip(context, Uri.fromFile(source), "test-bomb").isFailure)
    }
    @Test fun recordsAndServerJobSurviveWorkspaceReopen() {
        LocalWorkspace(context).use { store ->
            store.save(ProductRecord(id = "p1", batchId = "b1", brand = "QV", productNameEn = "Gentle Wash", createdAt = Timestamp(Date(0))))
            store.save(BatchJob(id = "b1", title = "real persisted workspace", status = BatchStatus.PAUSED.name))
            store.save(RemoteLink("p1", "b1", "input", "photo_discover", "remote", state = "RUNNING"))
        }
        LocalWorkspace(context).use { store ->
            assertEquals("QV", store.products().single().brand)
            assertEquals(0L, store.products().single().createdAt!!.toDate().time)
            assertEquals(BatchStatus.PAUSED, store.batches().single().statusEnum())
            assertEquals("remote", store.links().single().remoteBatchId)
            assertEquals("RUNNING", store.links().single().state)
        }
    }
    @Test fun failedLocalTransactionDoesNotLeaveHalfBatch() {
        LocalWorkspace(context).use { store ->
            runCatching { store.transaction { store.save(BatchJob(id = "rollback")); error("interrupted") } }
            assertTrue(store.batches().isEmpty())
        }
    }
    @Test fun backendRequiresHttpsAndNeverMarksMissingTokenConfigured() {
        val gateway = BackendGateway(context)
        assertFalse(gateway.configured())
        assertTrue(runCatching { gateway.saveConnection("http://localhost", "") }.isFailure)
        assertTrue(runCatching { gateway.saveConnection("https://user:secret@example.com", "") }.isFailure)
        gateway.saveConnection("https://engine.example.com", "")
        assertEquals("https://engine.example.com", gateway.endpoint)
        assertFalse(gateway.configured())
    }
    @Test fun changingBackendOriginCannotReuseOldToken() {
        val gateway = BackendGateway(context)
        gateway.saveConnection("https://first.example", "")
        context.getSharedPreferences("mhvie_backend", 0).edit().putString("token", "encrypted-token-placeholder").commit()
        assertTrue(runCatching { gateway.saveConnection("https://different.example", "") }.isFailure)
        assertEquals("https://first.example", gateway.endpoint)
        gateway.saveConnection("https://first.example/api", "")
        assertEquals("https://first.example/api", gateway.endpoint)
        assertEquals("encrypted-token-placeholder", context.getSharedPreferences("mhvie_backend", 0).getString("token", null))
    }
    @Test fun artifactCannotBeSavedWithoutExpectedFingerprint() {
        val target = File(context.filesDir, "unverified.png")
        assertTrue(runCatching { BackendGateway(context).download("v1/test", target) }.isFailure)
        assertFalse(target.exists())
    }

}
