package com.example.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp

private val LightColorScheme = lightColorScheme(
    primary = RoseBerryPrimary,
    onPrimary = RoseBerryOnPrimary,
    primaryContainer = RoseBerryContainer,
    onPrimaryContainer = RoseBerryOnContainer,
    secondary = ChampagneGoldSecondary,
    onSecondary = ChampagneOnSecondary,
    secondaryContainer = ChampagneContainer,
    onSecondaryContainer = ChampagneOnContainer,
    tertiary = PlumTertiary,
    onTertiary = PlumOnTertiary,
    tertiaryContainer = PlumContainer,
    onTertiaryContainer = PlumOnContainer,
    background = IvoryBackground,
    onBackground = EspressoOnBackground,
    surface = IvorySurface,
    onSurface = EspressoOnBackground,
    surfaceVariant = SoftBlushSurfaceVariant,
    onSurfaceVariant = EspressoMutedOnSurface,
    outline = SubtleRoseOutline,
    error = ErrorCrimson,
    errorContainer = ErrorCrimsonContainer
)

private val DarkColorScheme = darkColorScheme(
    primary = DarkRosePrimary,
    onPrimary = DarkRoseOnPrimary,
    primaryContainer = DarkRoseContainer,
    onPrimaryContainer = RoseBerryContainer,
    secondary = DarkChampagneSecondary,
    onSecondary = Color(0xFF472914),
    secondaryContainer = DarkChampagneContainer,
    onSecondaryContainer = ChampagneContainer,
    tertiary = Color(0xFFD6B9EE),
    onTertiary = Color(0xFF3B244D),
    tertiaryContainer = Color(0xFF503963),
    onTertiaryContainer = PlumContainer,
    background = DarkObsidianBackground,
    onBackground = Color(0xFFF3E8EA),
    surface = DarkObsidianSurface,
    onSurface = Color(0xFFF3E8EA),
    surfaceVariant = DarkSurfaceVariant,
    onSurfaceVariant = Color(0xFFD7C2C5),
    outline = Color(0xFF9F8C90),
    error = Color(0xFFFFB4AB),
    errorContainer = Color(0xFF93000A)
)

val MhvieShapes = Shapes(
    small = RoundedCornerShape(10.dp),
    medium = RoundedCornerShape(16.dp),
    large = RoundedCornerShape(24.dp),
    extraLarge = RoundedCornerShape(28.dp)
)

@Composable
fun MakeupHouseTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        shapes = MhvieShapes,
        content = content
    )
}
