package com.example.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.model.ProductStatus

enum class ExportFormat { ZIP, CSV_EXCEL, HTML_GALLERY, JSON }

@Composable
fun SectionHeader(title: String, trailing: String = "") {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
        if (trailing.isNotEmpty()) Text(trailing, style = MaterialTheme.typography.labelMedium)
    }
}

@Composable
fun EmptyStatePanel(icon: ImageVector, title: String, subtitle: String) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(icon, contentDescription = null, modifier = Modifier.size(32.dp))
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(subtitle, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
fun ProductStatusChip(status: ProductStatus) {
    Surface(shape = MaterialTheme.shapes.small, color = if (status == ProductStatus.FAILED) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.secondaryContainer) {
        Text(status.labelAr, Modifier.padding(horizontal = 8.dp, vertical = 6.dp), style = MaterialTheme.typography.labelSmall)
    }
}

@Composable
fun Notice(message: String) {
    Surface(Modifier.fillMaxWidth(), shape = MaterialTheme.shapes.medium, color = MaterialTheme.colorScheme.surfaceVariant) {
        Text(message, Modifier.padding(12.dp), style = MaterialTheme.typography.bodyMedium)
    }
}
