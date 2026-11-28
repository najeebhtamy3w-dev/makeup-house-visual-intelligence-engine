package com.example.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Collections
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.model.ApprovalStatus
import com.example.model.ProductRecord
import com.example.model.ProductStatus
import com.example.model.UiState
import java.io.File

@Composable
fun GalleryScreen(
    productsState: UiState<List<ProductRecord>>,
    onOpenProduct: (String) -> Unit,
    onBatchApprove: (Set<String>) -> Unit,
    modifier: Modifier = Modifier
) {
    val products = (productsState as? UiState.Success)?.data.orEmpty()
    var searchQuery by remember { mutableStateOf("") }
    var statusFilter by remember { mutableStateOf<ProductStatus?>(null) }
    var selectedIds by remember { mutableStateOf<Set<String>>(emptySet()) }

    val filtered = products.filter { p ->
        val matchesQuery = searchQuery.isBlank() ||
            p.displayTitle().contains(searchQuery, ignoreCase = true) ||
            p.brand.contains(searchQuery, ignoreCase = true) ||
            p.barcode.contains(searchQuery, ignoreCase = true)
        val matchesStatus = statusFilter == null || p.statusEnum() == statusFilter
        matchesQuery && matchesStatus
    }

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            SectionHeader(
                title = "المعرض البصري للمنتجات",
                trailing = "${filtered.size} منتج"
            )
        }

        item {
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { searchQuery = it },
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                placeholder = { Text("ابحث بالاسم، الماركة، أو الباركود...") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
            )
        }

        item {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                item {
                    FilterChip(
                        selected = statusFilter == null,
                        onClick = { statusFilter = null },
                        label = { Text("الكل") }
                    )
                }
                listOf(ProductStatus.FOUND, ProductStatus.REVIEW_REQUIRED, ProductStatus.ZERO_RESULT).forEach { st ->
                    item {
                        FilterChip(
                            selected = statusFilter == st,
                            onClick = { statusFilter = if (statusFilter == st) null else st },
                            label = { Text(st.labelAr) }
                        )
                    }
                }
            }
        }

        if (selectedIds.isNotEmpty()) {
            item {
                Surface(
                    color = MaterialTheme.colorScheme.primaryContainer,
                    shape = MaterialTheme.shapes.medium,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("تم تحديد ${selectedIds.size} منتج", fontWeight = FontWeight.Bold)
                        Button(onClick = {
                            onBatchApprove(selectedIds)
                            selectedIds = emptySet()
                        }) {
                            Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("اعتماد جماعي")
                        }
                    }
                }
            }
        }

        if (filtered.isEmpty()) {
            item {
                EmptyStatePanel(
                    icon = Icons.Default.Collections,
                    title = "لا توجد منتجات مطابقة",
                    subtitle = "جرّب تغيير فلتر البحث أو إضافة دفعة منتجات جديدة."
                )
            }
        } else {
            items(filtered, key = { it.id }) { product ->
                val isChecked = product.id in selectedIds
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onOpenProduct(product.id) },
                    shape = MaterialTheme.shapes.medium,
                    border = if (isChecked) BorderStroke(2.dp, MaterialTheme.colorScheme.primary) else null,
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Checkbox(
                            checked = isChecked,
                            onCheckedChange = { checked ->
                                selectedIds = if (checked) selectedIds + product.id else selectedIds - product.id
                            }
                        )
                        val imgModel: Any? = product.bestImageUrl.takeIf { it.isNotBlank() }
                            ?: product.localOriginalPaths.firstOrNull()?.let { File(it) }
                        AsyncImage(
                            model = imgModel,
                            contentDescription = product.displayTitle(),
                            contentScale = ContentScale.Crop,
                            modifier = Modifier
                                .size(72.dp)
                                .clip(MaterialTheme.shapes.small)
                        )
                        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(
                                text = product.displayTitle(),
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "مطابق: ${product.matchedCount} من ${product.discoveredCount} • ${product.approvalEnum().labelAr}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            ProductStatusChip(product.statusEnum())
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ZeroResultScreen(
    productsState: UiState<List<ProductRecord>>,
    onOpenProduct: (String) -> Unit,
    onReprocess: (ProductRecord) -> Unit,
    onSendToStudio: (ProductRecord) -> Unit,
    modifier: Modifier = Modifier
) {
    val zeroProducts = (productsState as? UiState.Success)?.data.orEmpty()
        .filter { it.statusEnum() == ProductStatus.ZERO_RESULT || it.statusEnum() == ProductStatus.FAILED }

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            SectionHeader(
                title = "المنتجات ذات النتيجة صفر (0 — NO SUITABLE IMAGE)",
                trailing = "${zeroProducts.size} منتج"
            )
        }

        if (zeroProducts.isEmpty()) {
            item {
                EmptyStatePanel(
                    icon = Icons.Default.CheckCircle,
                    title = "لا توجد منتجات بنتيجة صفر حاليًا",
                    subtitle = "جميع المنتجات المعالجة حصلت على صور مطابقة أو قيد المراجعة."
                )
            }
        } else {
            items(zeroProducts, key = { it.id }) { prod ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onOpenProduct(prod.id) },
                    shape = MaterialTheme.shapes.medium,
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            AsyncImage(
                                model = prod.localOriginalPaths.firstOrNull()?.let { File(it) },
                                contentDescription = prod.displayTitle(),
                                contentScale = ContentScale.Crop,
                                modifier = Modifier
                                    .size(72.dp)
                                    .clip(MaterialTheme.shapes.small)
                            )
                            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(prod.displayTitle(), style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                                Surface(
                                    color = MaterialTheme.colorScheme.errorContainer,
                                    shape = MaterialTheme.shapes.small
                                ) {
                                    Text(
                                        text = "السبب: ${prod.zeroReasonEnum().labelAr}",
                                        color = MaterialTheme.colorScheme.error,
                                        style = MaterialTheme.typography.labelSmall,
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                    )
                                }
                            }
                        }

                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                            OutlinedButton(
                                onClick = { onReprocess(prod) },
                                modifier = Modifier.weight(1f)
                            ) {
                                Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(Modifier.width(4.dp))
                                Text("إعادة البحث")
                            }
                            Button(
                                onClick = { onSendToStudio(prod) },
                                modifier = Modifier.weight(1f)
                            ) {
                                Icon(Icons.Default.AutoAwesome, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(Modifier.width(4.dp))
                                Text("إرسال للاستوديو")
                            }
                        }
                    }
                }
            }
        }
    }
}
