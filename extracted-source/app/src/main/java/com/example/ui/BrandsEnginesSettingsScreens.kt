package com.example.ui

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Backup
import androidx.compose.material.icons.filled.Logout
import androidx.compose.material.icons.filled.Restore
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.Storefront
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.core.EngineSettings
import com.example.model.BrandProfile
import com.example.model.EngineAuditLog
import com.example.model.EngineConfig
import com.example.model.UiState
import com.example.ui.theme.ErrorCrimson
import com.example.ui.theme.VerifiedSage
import com.example.ui.theme.WarningAmber

@Composable
fun BrandLibraryScreen(
    brandsState: UiState<List<BrandProfile>>,
    onUpsertBrand: (BrandProfile) -> Unit,
    modifier: Modifier = Modifier
) {
    val brands = (brandsState as? UiState.Success)?.data.orEmpty()
    var showAddDialog by remember { mutableStateOf(false) }

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("مكتبة الماركات والذاكرة التجارية", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Button(onClick = { showAddDialog = true }) {
                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(4.dp))
                    Text("إضافة")
                }
            }
        }

        if (brands.isEmpty()) {
            item {
                EmptyStatePanel(
                    icon = Icons.Default.Storefront,
                    title = "مكتبة الماركات فارغة حاليًا",
                    subtitle = "تُبنى تلقائيًا أثناء معالجة المنتجات، أو يمكنك إضافة مواقع وحسابات الماركات يدويًا لتسريع البحث."
                )
            }
        } else {
            items(brands, key = { it.id }) { brand ->
                Card(
                    shape = MaterialTheme.shapes.medium,
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(brand.brandName, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Text(
                                text = "نجاح ${(brand.successRate * 100).toInt()}% • ${brand.processedCount} منتج",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }
                        if (brand.officialWebsite.isNotBlank()) {
                            Text("الموقع الرسمي: ${brand.officialWebsite}", style = MaterialTheme.typography.bodySmall)
                        }
                        if (brand.instagramHandle.isNotBlank()) {
                            Text("Instagram: ${brand.instagramHandle}", style = MaterialTheme.typography.bodySmall)
                        }
                        if (brand.pinterestHandle.isNotBlank()) {
                            Text("Pinterest: ${brand.pinterestHandle}", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
    }

    if (showAddDialog) {
        var name by remember { mutableStateOf("") }
        var site by remember { mutableStateOf("") }
        var ig by remember { mutableStateOf("") }
        var pin by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { showAddDialog = false },
            title = { Text("إضافة أو تحديث ماركة") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("اسم الماركة") }, singleLine = true)
                    OutlinedTextField(value = site, onValueChange = { site = it }, label = { Text("الموقع الرسمي (https://...)") }, singleLine = true)
                    OutlinedTextField(value = ig, onValueChange = { ig = it }, label = { Text("حساب Instagram العام") }, singleLine = true)
                    OutlinedTextField(value = pin, onValueChange = { pin = it }, label = { Text("حساب Pinterest العام") }, singleLine = true)
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (name.isNotBlank()) {
                            onUpsertBrand(
                                BrandProfile(
                                    brandName = name.trim(),
                                    officialWebsite = site.trim(),
                                    instagramHandle = ig.trim(),
                                    pinterestHandle = pin.trim()
                                )
                            )
                            showAddDialog = false
                        }
                    }
                ) { Text("حفظ") }
            },
            dismissButton = {
                TextButton(onClick = { showAddDialog = false }) { Text("إلغاء") }
            }
        )
    }
}

@Composable
fun EngineManagerScreen(
    enginesState: UiState<List<EngineConfig>>,
    isBenchmarking: Boolean,
    onToggleEngine: (EngineConfig, Boolean) -> Unit,
    onUpdateEndpoint: (EngineConfig, String) -> Unit,
    onRunBenchmarks: () -> Unit,
    modifier: Modifier = Modifier
) {
    val engines = (enginesState as? UiState.Success)?.data.orEmpty()

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            SectionHeader(title = "إدارة المحركات والاختبار الفعلي")
        }

        item {
            Button(
                onClick = onRunBenchmarks,
                enabled = !isBenchmarking,
                modifier = Modifier.fillMaxWidth()
            ) {
                if (isBenchmarking) {
                    CircularProgressIndicator(Modifier.size(18.dp), color = MaterialTheme.colorScheme.onPrimary, strokeWidth = 2.dp)
                    Spacer(Modifier.width(8.dp))
                    Text("جاري اختبار المحركات فعليًا...")
                } else {
                    Icon(Icons.Default.Speed, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("تشغيل اختبار الاتصال والأداء الفعلي (Benchmark)")
                }
            }
        }

        items(engines, key = { it.engineKey }) { engine ->
            var endpointInput by remember(engine.engineKey, engine.endpointUrl) { mutableStateOf(engine.endpointUrl) }
            val statusColor = when (engine.lastHealthStatus) {
                "READY" -> VerifiedSage
                "UNCONFIGURED" -> WarningAmber
                else -> ErrorCrimson
            }
            Card(
                shape = MaterialTheme.shapes.medium,
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(engine.displayName, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                            Text(
                                text = "الأولوية: ${engine.priorityOrder} • التكلفة: ${engine.costTier} • زمن الاستجابة: ${engine.lastLatencyMs}ms",
                                style = MaterialTheme.typography.labelSmall,
                                color = statusColor
                            )
                        }
                        Switch(
                            checked = engine.enabled,
                            onCheckedChange = { onToggleEngine(engine, it) }
                        )
                    }
                    if (engine.lastTestSummary.isNotBlank()) {
                        Text(engine.lastTestSummary, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    if (engine.engineKey == "searxng_meta") {
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            OutlinedTextField(
                                value = endpointInput,
                                onValueChange = { endpointInput = it },
                                label = { Text("رابط خادم SearXNG (https://...)") },
                                singleLine = true,
                                modifier = Modifier.weight(1f)
                            )
                            Button(onClick = { onUpdateEndpoint(engine, endpointInput) }) {
                                Text("حفظ")
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun SettingsAndExportScreen(
    settings: EngineSettings,
    logsState: UiState<List<EngineAuditLog>>,
    userEmail: String?,
    onUpdateSettings: ((EngineSettings) -> EngineSettings) -> Unit,
    onExportBackup: () -> Unit,
    onRestoreBackup: (Uri) -> Unit,
    onOpenBrands: () -> Unit,
    onOpenEngines: () -> Unit,
    onOpenZeroResults: () -> Unit,
    onSignOut: () -> Unit,
    modifier: Modifier = Modifier
) {
    val logs = (logsState as? UiState.Success)?.data.orEmpty()
    val restorePicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) onRestoreBackup(uri)
    }

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            SectionHeader(title = "الإدارة والأدوات المتقدمة")
        }

        // Quick-access cards for mobile screens
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    OutlinedButton(
                        onClick = onOpenBrands,
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.Storefront, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("مكتبة الماركات")
                    }
                    OutlinedButton(
                        onClick = onOpenEngines,
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.Speed, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("المحركات والفحص")
                    }
                }
                OutlinedButton(
                    onClick = onOpenZeroResults,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("مراجعة المنتجات ذات النتيجة صفر (Zero-Result)")
                }
            }
        }

        item {
            SectionHeader(title = "الإعدادات والنسخ الاحتياطي")
        }

        // Account Card
        item {
            Card(
                shape = MaterialTheme.shapes.medium,
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(14.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("الحساب المرتبط", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(userEmail ?: "مستخدم Google", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                    }
                    OutlinedButton(onClick = onSignOut) {
                        Icon(Icons.Default.Logout, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("تسجيل الخروج")
                    }
                }
            }
        }

        // Thresholds Card
        item {
            Card(
                shape = MaterialTheme.shapes.medium,
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("عتبات المطابقة والجودة", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text("الحد الأدنى لدرجة مطابقة المنتج: ${(settings.minMatchScore * 100).toInt()}%")
                    Slider(
                        value = settings.minMatchScore.toFloat(),
                        onValueChange = { v -> onUpdateSettings { it.copy(minMatchScore = v.toDouble()) } },
                        valueRange = 0.4f..0.95f
                    )
                    Text("الحد الأدنى لجودة الصورة وجماليتها: ${(settings.minAestheticScore * 100).toInt()}%")
                    Slider(
                        value = settings.minAestheticScore.toFloat(),
                        onValueChange = { v -> onUpdateSettings { it.copy(minAestheticScore = v.toDouble()) } },
                        valueRange = 0.25f..0.90f
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("التوقف التصاعدي التلقائي عند كفاية الصور")
                        Switch(
                            checked = settings.autoStopOnSufficientImages,
                            onCheckedChange = { checked -> onUpdateSettings { it.copy(autoStopOnSufficientImages = checked) } }
                        )
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("تفعيل البحث الاجتماعي المفهرس (L3)")
                        Switch(
                            checked = settings.enableSocialDiscovery,
                            onCheckedChange = { checked -> onUpdateSettings { it.copy(enableSocialDiscovery = checked) } }
                        )
                    }
                }
            }
        }

        // Backup & Restore Card
        item {
            Card(
                shape = MaterialTheme.shapes.medium,
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("النسخ الاحتياطي والاسترجاع (Knowledge Base)", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                        Button(onClick = onExportBackup, modifier = Modifier.weight(1f)) {
                            Icon(Icons.Default.Backup, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("تصدير نسخة JSON")
                        }
                        OutlinedButton(
                            onClick = { restorePicker.launch(arrayOf("application/json", "*/*")) },
                            modifier = Modifier.weight(1f)
                        ) {
                            Icon(Icons.Default.Restore, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("استرجاع نسخة")
                        }
                    }
                }
            }
        }

        // Audit & Error Logs
        item {
            SectionHeader(title = "سجل الأخطاء وقرارات المنسّق", trailing = "${logs.size} سجل")
        }

        if (logs.isEmpty()) {
            item {
                Text("لا توجد أخطاء مسجلة.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        } else {
            items(logs.take(25), key = { it.id }) { log ->
                Surface(
                    shape = MaterialTheme.shapes.small,
                    color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(10.dp)) {
                        Text(
                            text = "[${log.level}] ${log.component}",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = if (log.level == "ERROR") ErrorCrimson else MaterialTheme.colorScheme.primary
                        )
                        Text(log.message, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
    }
}
