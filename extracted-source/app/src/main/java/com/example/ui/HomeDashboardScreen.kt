package com.example.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.engine.OrchestratorProgress
import com.example.model.*

@Composable
fun HomeDashboardScreen(
    batchesState: UiState<List<BatchJob>>, productsState: UiState<List<ProductRecord>>,
    enginesState: UiState<List<EngineConfig>>, orchestratorProgress: OrchestratorProgress,
    onNavigateNewBatch: () -> Unit, onOpenBatchMonitor: (String) -> Unit,
    onOpenEngines: () -> Unit, onOpenZeroResults: () -> Unit
) {
    val batches = (batchesState as? UiState.Success)?.data.orEmpty()
    val products = (productsState as? UiState.Success)?.data.orEmpty()
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        item {
            Text("MH-VIE", style = MaterialTheme.typography.headlineLarge)
            Text("مكتبتك البصرية ومصنع محتوى المنتجات", style = MaterialTheme.typography.titleMedium)
        }
        item { Notice("الصور والمنتجات محفوظة على هذا الجهاز. الذكاء والبحث والاستوديو يعملون عبر خادمك المعرّف في الإعدادات. اكتمال المعالجة لا يعني اعتماد الهوية أو الحقوق.") }
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Card(Modifier.weight(1f)) { Column(Modifier.padding(16.dp)) { Text("${products.size}", style = MaterialTheme.typography.headlineMedium); Text("منتج") } }
                Card(Modifier.weight(1f)) { Column(Modifier.padding(16.dp)) { Text("${batches.size}", style = MaterialTheme.typography.headlineMedium); Text("دفعة") } }
            }
        }
        item { Button(onClick = onNavigateNewBatch, modifier = Modifier.fillMaxWidth()) { Text("تصوير منتج أو إنشاء دفعة") } }
        item { OutlinedButton(onClick = onOpenEngines, modifier = Modifier.fillMaxWidth()) { Text("اتصال المحركات وحالتها الفعلية") } }
        if (orchestratorProgress.lastDecisionNote.isNotBlank()) item { Notice(orchestratorProgress.lastDecisionNote) }
        item { SectionHeader("آخر الدفعات") }
        items(batches.take(10), key = { it.id }) { batch ->
            Card(onClick = { onOpenBatchMonitor(batch.id) }, modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) { Text(batch.title); Text("${batch.processedProducts}/${batch.totalProducts} • ${batch.statusEnum().labelAr}") }
            }
        }
        if (products.any { it.statusEnum() in setOf(ProductStatus.ZERO_RESULT, ProductStatus.FAILED) }) item {
            OutlinedButton(onClick = onOpenZeroResults) { Text("مراجعة المنتجات التي لم تكتمل") }
        }
    }
}
