package com.example.ui

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.example.model.SearchStrategy
import java.io.File

@Composable
fun NewBatchScreen(
    defaultTargetImages: Int,
    onStartBatchFromPhotos: (String, List<Uri>, Boolean, Uri?, SearchStrategy, Int) -> Unit,
    onStartBatchFromZip: (String, Uri, Uri?, SearchStrategy, Int) -> Unit
) {
    val context = LocalContext.current
    var title by rememberSaveable { mutableStateOf("") }
    var photos by remember { mutableStateOf<List<Uri>>(emptyList()) }
    var zip by remember { mutableStateOf<Uri?>(null) }
    var csv by remember { mutableStateOf<Uri?>(null) }
    var grouped by rememberSaveable { mutableStateOf(false) }
    var target by rememberSaveable { mutableStateOf(defaultTargetImages.coerceIn(1,20).toString()) }
    var cameraUri by rememberSaveable { mutableStateOf<String?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    val gallery = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { selected ->
        if (selected.isNotEmpty()) { photos = selected; zip = null }
    }
    val archive = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { selected -> if (selected != null) { zip = selected; photos = emptyList() } }
    val csvPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { csv = it }
    val camera = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { success -> if (success) cameraUri?.let { photos = photos + Uri.parse(it); zip = null } }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { SectionHeader("إدخال المنتجات والدفعات") }
        item { Notice("ستُحفظ النسخ الأصلية محليًا. بدء المعالجة يرفع الصور إلى خادم MH-VIE الذي ضبطته؛ عند غياب الاتصال تبقى الدفعة في الانتظار. CSV اختياري: sku,brand,name,size,shade,barcode.") }
        item { OutlinedTextField(title, { title = it }, label = { Text("اسم الدفعة") }, modifier = Modifier.fillMaxWidth(), singleLine = true) }
        item { Button(onClick = { gallery.launch(arrayOf("image/*")) }, modifier = Modifier.fillMaxWidth()) { Text("اختيار صور متعددة (${photos.size})") } }
        item { OutlinedButton(onClick = {
            try {
                val folder = File(context.filesDir, "mhvie_images/camera").apply { mkdirs() }
                val file = File.createTempFile("capture_", ".jpg", folder)
                val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
                cameraUri = uri.toString(); camera.launch(uri)
            } catch (e: Exception) { error = "تعذر فتح الكاميرا" }
        }, modifier = Modifier.fillMaxWidth()) { Text("التقاط صورة بالكاميرا") } }
        item { OutlinedButton(onClick = { archive.launch(arrayOf("application/zip", "application/x-zip-compressed")) }, modifier = Modifier.fillMaxWidth()) { Text(if (zip == null) "استيراد ZIP" else "تم اختيار ZIP") } }
        item { OutlinedButton(onClick = { csvPicker.launch(arrayOf("text/*", "application/csv")) }, modifier = Modifier.fillMaxWidth()) { Text(if (csv == null) "إرفاق CSV اختياري" else "CSV مرفق") } }
        item { Row(Modifier.fillMaxWidth()) { Checkbox(grouped, { grouped = it }); Text("الصور المحددة لمنتج واحد (أوقفه: كل صورة منتج)") } }
        item { OutlinedTextField(target, { target = it.filter(Char::isDigit).take(2) }, label = { Text("الصور المطلوبة لكل منتج (1–20)") }, singleLine = true, modifier = Modifier.fillMaxWidth()) }
        error?.let { item { Text(it, color = MaterialTheme.colorScheme.error) } }
        item { Button(onClick = {
            val count = target.toIntOrNull()?.coerceIn(1,20) ?: defaultTargetImages
            if (zip != null) onStartBatchFromZip(title, zip!!, csv, SearchStrategy.STANDARD, count)
            else onStartBatchFromPhotos(title, photos, grouped, csv, SearchStrategy.STANDARD, count)
        }, enabled = photos.isNotEmpty() || zip != null, modifier = Modifier.fillMaxWidth()) { Text("حفظ الدفعة وبدء المعالجة") } }
    }
}
