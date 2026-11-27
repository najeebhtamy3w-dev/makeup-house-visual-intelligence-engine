package com.example.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.model.*
import java.io.File

@Composable
fun ProductDetailScreen(
    product: ProductRecord?, candidatesState: UiState<List<DiscoveredImage>>, studioState: StudioUiState,
    onBack: () -> Unit, onReprocess: (ProductRecord) -> Unit,
    onApproveCandidate: (String, DiscoveredImage) -> Unit,
    onRejectCandidate: (String, String) -> Unit,
    onDownloadCandidate: (String, DiscoveredImage) -> Unit,
    onGenerateStudio: (ProductRecord, String) -> Unit,
    onSaveIdentity: (ProductRecord) -> Unit,
    onReadBarcode: (ProductRecord) -> Unit,
    onShareStudio: (String) -> Unit
) {
    if (product == null) { Column(Modifier.padding(16.dp)) { Text("لم يُعثر على المنتج"); TextButton(onClick = onBack) { Text("رجوع") } }; return }
    var name by remember(product.id, product.productNameEn) { mutableStateOf(product.productNameEn.ifBlank { product.productNameAr }) }
    var brand by remember(product.id, product.brand) { mutableStateOf(product.brand) }
    var size by remember(product.id, product.sizeWeight) { mutableStateOf(product.sizeWeight) }
    var barcode by remember(product.id, product.barcode) { mutableStateOf(product.barcode) }
    var prompt by remember(product.id) { mutableStateOf("") }
    var identityConfirmed by remember(product.id) { mutableStateOf(false) }
    val candidates = (candidatesState as? UiState.Success)?.data.orEmpty()
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { TextButton(onClick = onBack) { Text("رجوع") }; SectionHeader(product.displayTitle()) }
        item { AsyncImage(model = product.localOriginalPaths.firstOrNull()?.let(::File), contentDescription = "الصورة الأصلية المحفوظة", contentScale = ContentScale.Fit, modifier = Modifier.fillMaxWidth().height(260.dp)) }
        item { ProductStatusChip(product.statusEnum()); Text(product.orchestratorNotes) }
        item { Notice("حقول الذكاء مقترحات تحتاج إلى مراجعة. درجات الهوية غير المعايرة لا تُعرض كنسبة ثقة. اعتماد الصورة جماليًا لا يجيز استخدامها تجاريًا؛ الحقوق مستقلة.") }
        item { OutlinedTextField(brand, { brand = it }, label = { Text("الماركة") }, modifier = Modifier.fillMaxWidth()) }
        item { OutlinedTextField(name, { name = it }, label = { Text("اسم المنتج") }, modifier = Modifier.fillMaxWidth()) }
        item { OutlinedTextField(size, { size = it }, label = { Text("الحجم أو التركيز") }, modifier = Modifier.fillMaxWidth()) }
        item { OutlinedTextField(barcode, { barcode = it }, label = { Text("الباركود") }, modifier = Modifier.fillMaxWidth(), singleLine = true) }
        item { Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { onSaveIdentity(product.copy(brand = brand, productNameEn = name, sizeWeight = size, barcode = barcode)) }, modifier = Modifier.weight(1f)) { Text("حفظ التصحيح") }
            OutlinedButton(onClick = { onReadBarcode(product) }, modifier = Modifier.weight(1f)) { Text("قراءة الباركود من الأصل") }
        } }
        item { OutlinedButton(onClick = { onReprocess(product) }, modifier = Modifier.fillMaxWidth()) { Text("إعادة التعرف والبحث بالمحرك") } }
        item { SectionHeader("صور مرشحة للمراجعة", "${candidates.size}") }
        items(candidates, key = { it.id }) { candidate ->
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (candidate.localSavedPath.isNotBlank()) AsyncImage(model = File(candidate.localSavedPath), contentDescription = "مرشح للمراجعة", contentScale = ContentScale.Fit, modifier = Modifier.fillMaxWidth().height(220.dp))
                    Text("${candidate.widthPx} × ${candidate.heightPx} • ${candidate.categoryEnum().labelAr}")
                    Text("الحالة: ${candidate.decisionEnum().labelAr} • ${candidate.rightsEnum().labelAr}")
                    Text("المصدر: ${candidate.pageUrl}", style = MaterialTheme.typography.bodySmall)
                    Text(candidate.verificationNotes, style = MaterialTheme.typography.bodySmall, maxLines = 10)
                    OutlinedButton(onClick = { onDownloadCandidate(product.id, candidate) }, modifier = Modifier.fillMaxWidth()) { Text("تنزيل نسخة المراجعة من خادمك والتحقق من بصمتها") }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { onApproveCandidate(product.id, candidate) }, enabled = candidate.categoryEnum() != ImageCategory.G_MISMATCH && candidate.localSavedPath.isNotBlank()) { Text("اختيار الصورة") }
                        OutlinedButton(onClick = { onRejectCandidate(product.id, candidate.id) }) { Text("رفض") }
                    }
                }
            }
        }
        item { SectionHeader("الاستوديو الإبداعي") }
        item { Notice("تحرير مباشر عبر خادمك دون فرض قناع. قد تتغير تفاصيل العبوة؛ الصورة الأصلية محفوظة ويجب مقارنة الشعار والنص والحجم قبل الاعتماد. لا نشر تلقائي.") }
        item { OutlinedTextField(prompt, { prompt = it.take(1500) }, label = { Text("وصف التعديل بالعربية أو الإنجليزية") }, placeholder = { Text("ضع المنتج على سطح رخامي بإضاءة فاخرة وحافظ على العبوة والكتابة") }, modifier = Modifier.fillMaxWidth(), minLines = 3) }
        item { Row { Checkbox(identityConfirmed, { identityConfirmed = it }); Text("أفهم أن النتيجة تتطلب فحص هوية المنتج والحقوق قبل استخدامها") } }
        item { Button(onClick = { onGenerateStudio(product, prompt) }, enabled = prompt.isNotBlank() && identityConfirmed && studioState !is StudioUiState.Working, modifier = Modifier.fillMaxWidth()) { Text("إرسال أمر التحرير") } }
        item { when (studioState) {
            StudioUiState.Idle -> Text("لم تبدأ مهمة تحرير")
            is StudioUiState.Working -> { CircularProgressIndicator(); Text(studioState.message) }
            is StudioUiState.Error -> Text(studioState.message, color = MaterialTheme.colorScheme.error)
            is StudioUiState.Ready -> Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                AsyncImage(model = File(studioState.path), contentDescription = "ناتج الاستوديو يحتاج مراجعة", contentScale = ContentScale.Fit, modifier = Modifier.fillMaxWidth().height(320.dp))
                Text("ناتج حقيقي من المحرك؛ غير معتمد للنشر")
                Text(studioState.evidence, style = MaterialTheme.typography.bodySmall, maxLines = 16)
                OutlinedButton(onClick = { onShareStudio(studioState.path) }) { Text("مشاركة نسخة المراجعة") }
            }
        } }
    }
}
