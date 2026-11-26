package com.example.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.engine.OrchestratorProgress
import com.example.model.BatchJob
import com.example.model.BatchStatus
import com.example.model.ProductRecord
import com.example.model.UiState
import java.io.File

@Composable
fun BatchMonitorScreen(
    batchesState: UiState<List<BatchJob>>,
    productsState: UiState<List<ProductRecord>>,
    selectedBatchId: String?,
    orchestratorProgress: OrchestratorProgress,
    onSelectBatch: (String) -> Unit,
    onPauseBatch: () -> Unit,
    onResumeBatch: (BatchJob) -> Unit,
    onRetryFailed: (BatchJob) -> Unit,
    onExportBatch: (BatchJob, ExportFormat) -> Unit,
    onOpenProduct: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    val batches = (batchesState as? UiState.Success)?.data.orEmpty()
    val activeBatch = batches.firstOrNull { it.id == selectedBatchId } ?: batches.firstOrNull()
    val allProducts = (productsState as? UiState.Success)?.data.orEmpty()
    val batchProducts = if (activeBatch != null) allProducts.filter { it.batchId == activeBatch.id } else emptyList()

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            SectionHeader(title = "متابعة تنفيذ الدفعات")
        }

        if (batches.isNotEmpty()) {
            item {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(batches, key = { it.id }) { batch ->
                        FilterChip(
                            selected = activeBatch?.id == batch.id,
                            onClick = { onSelectBatch(batch.id) },
                            label = { Text(batch.title) }
                        )
                    }
                }
            }
        }

        if (activeBatch == null) {
            item {
                EmptyStatePanel(
                    icon = Icons.Default.PlayArrow,
                    title = "لا توجد دفعة محددة",
                    subtitle = "أنشئ دفعة جديدة لمتابعة تقدم التعرف والبحث والتحقق في الوقت الفعلي."
                )
            }
        } else {
            item {
                val pct = if (activeBatch.totalProducts > 0) {
                    activeBatch.processedProducts.toFloat() / activeBatch.totalProducts.toFloat()
                } else 0f

                Card(
                    shape = MaterialTheme.shapes.medium,
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(activeBatch.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Text(
                                text = "${(pct * 100).toInt()}%",
                                style = MaterialTheme.typography.titleLarge,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }

                        LinearProgressIndicator(
                            progress = { pct.coerceIn(0f, 1f) },
                            modifier = Modifier.fillMaxWidth()
                        )

                        Text(
                            text = "الحالة: ${activeBatch.statusEnum().labelAr} • الاستراتيجية: ${activeBatch.strategyEnum().labelAr}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )

                        if (orchestratorProgress.isRunning && orchestratorProgress.activeBatchId == activeBatch.id) {
                            Text(
                                text = "المنتج الجاري: ${orchestratorProgress.activeProductTitle} (${orchestratorProgress.activeLevel})",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.primary
                            )
                            Text(
                                text = "المحركات النشطة: ${orchestratorProgress.activeEngines.joinToString(" • ")}",
                                style = MaterialTheme.typography.labelSmall
                            )
                        }

                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                            if (activeBatch.statusEnum() == BatchStatus.RUNNING && orchestratorProgress.isRunning) {
                                Button(onClick = onPauseBatch, modifier = Modifier.weight(1f)) {
                                    Icon(Icons.Default.Pause, contentDescription = null, modifier = Modifier.size(18.dp))
                                    Spacer(Modifier.width(6.dp))
                                    Text("إيقاف مؤقت")
                                }
                            } else {
                                Button(onClick = { onResumeBatch(activeBatch) }, modifier = Modifier.weight(1f)) {
                                    Icon(Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(18.dp))
                                    Spacer(Modifier.width(6.dp))
                                    Text("استئناف / تشغيل")
                                }
                            }
                            OutlinedButton(onClick = { onRetryFailed(activeBatch) }, modifier = Modifier.weight(1f)) {
                                Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(18.dp))
                                Spacer(Modifier.width(6.dp))
                                Text("إعادة الفاشلة")
                            }
                        }

                        // Export Actions Row
                        Text("تصدير نتائج الدفعة:", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold)
                        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            item {
                                OutlinedButton(onClick = { onExportBatch(activeBatch, ExportFormat.ZIP) }) {
                                    Icon(Icons.Default.Download, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(Modifier.width(4.dp))
                                    Text("ZIP كامل")
                                }
                            }
                            item {
                                OutlinedButton(onClick = { onExportBatch(activeBatch, ExportFormat.CSV_EXCEL) }) {
                                    Text("تقرير Excel CSV")
                                }
                            }
                            item {
                                OutlinedButton(onClick = { onExportBatch(activeBatch, ExportFormat.HTML_GALLERY) }) {
                                    Text("معرض HTML")
                                }
                            }
                            item {
                                OutlinedButton(onClick = { onExportBatch(activeBatch, ExportFormat.JSON) }) {
                                    Text("JSON")
                                }
                            }
                        }
                    }
                }
            }

            item {
                SectionHeader(title = "المنتجات في هذه الدفعة", trailing = "${batchProducts.size} منتج")
            }

            items(batchProducts, key = { it.id }) { prod ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onOpenProduct(prod.id) },
                    shape = MaterialTheme.shapes.medium,
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        val thumbModel: Any? = prod.bestImageUrl.takeIf { it.isNotBlank() }
                            ?: prod.localOriginalPaths.firstOrNull()?.let { File(it) }
                        AsyncImage(
                            model = thumbModel,
                            contentDescription = prod.displayTitle(),
                            contentScale = ContentScale.Crop,
                            modifier = Modifier
                                .size(64.dp)
                                .clip(MaterialTheme.shapes.small)
                        )
                        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(
                                text = prod.displayTitle(),
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = listOf(prod.sizeWeight, prod.shadeColor, prod.barcode)
                                    .filter { it.isNotBlank() }
                                    .joinToString(" • ")
                                    .ifBlank { "المستوى: ${prod.escalationLevelReached}" },
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            if (prod.orchestratorNotes.isNotBlank()) {
                                Text(
                                    text = prod.orchestratorNotes,
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    maxLines = 2
                                )
                            }
                        }
                        ProductStatusChip(status = prod.statusEnum())
                    }
                }
            }
        }
    }
}
