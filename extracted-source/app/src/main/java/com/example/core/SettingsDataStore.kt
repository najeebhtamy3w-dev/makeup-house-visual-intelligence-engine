package com.example.core

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.doublePreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.mhvieDataStore: DataStore<Preferences> by preferencesDataStore(name = "mhvie_settings")

data class EngineSettings(
    val minMatchScore: Double = 0.65,
    val minAestheticScore: Double = 0.50,
    val defaultTargetImages: Int = 5,
    val maxConcurrentTasks: Int = 2,
    val searxngBaseUrl: String = "",
    val enableSocialDiscovery: Boolean = true,
    val enableCreativeStudio: Boolean = true,
    val autoStopOnSufficientImages: Boolean = true
)

class SettingsDataStore(private val context: Context) {
    private object Keys {
        val MIN_MATCH = doublePreferencesKey("min_match_score")
        val MIN_AESTHETIC = doublePreferencesKey("min_aesthetic_score")
        val TARGET_IMAGES = intPreferencesKey("default_target_images")
        val MAX_CONCURRENT = intPreferencesKey("max_concurrent_tasks")
        val SEARXNG_URL = stringPreferencesKey("searxng_base_url")
        val ENABLE_SOCIAL = booleanPreferencesKey("enable_social_discovery")
        val ENABLE_STUDIO = booleanPreferencesKey("enable_creative_studio")
        val AUTO_STOP = booleanPreferencesKey("auto_stop_on_sufficient")
    }

    val settingsFlow: Flow<EngineSettings> = context.mhvieDataStore.data.map { prefs ->
        EngineSettings(
            minMatchScore = prefs[Keys.MIN_MATCH] ?: 0.65,
            minAestheticScore = prefs[Keys.MIN_AESTHETIC] ?: 0.50,
            defaultTargetImages = prefs[Keys.TARGET_IMAGES] ?: 5,
            maxConcurrentTasks = prefs[Keys.MAX_CONCURRENT] ?: 2,
            searxngBaseUrl = prefs[Keys.SEARXNG_URL] ?: "",
            enableSocialDiscovery = prefs[Keys.ENABLE_SOCIAL] ?: true,
            enableCreativeStudio = prefs[Keys.ENABLE_STUDIO] ?: true,
            autoStopOnSufficientImages = prefs[Keys.AUTO_STOP] ?: true
        )
    }

    suspend fun updateSettings(transform: (EngineSettings) -> EngineSettings) {
        context.mhvieDataStore.edit { prefs ->
            val current = EngineSettings(
                minMatchScore = prefs[Keys.MIN_MATCH] ?: 0.65,
                minAestheticScore = prefs[Keys.MIN_AESTHETIC] ?: 0.50,
                defaultTargetImages = prefs[Keys.TARGET_IMAGES] ?: 5,
                maxConcurrentTasks = prefs[Keys.MAX_CONCURRENT] ?: 2,
                searxngBaseUrl = prefs[Keys.SEARXNG_URL] ?: "",
                enableSocialDiscovery = prefs[Keys.ENABLE_SOCIAL] ?: true,
                enableCreativeStudio = prefs[Keys.ENABLE_STUDIO] ?: true,
                autoStopOnSufficientImages = prefs[Keys.AUTO_STOP] ?: true
            )
            val updated = transform(current)
            prefs[Keys.MIN_MATCH] = updated.minMatchScore.coerceIn(0.3, 0.95)
            prefs[Keys.MIN_AESTHETIC] = updated.minAestheticScore.coerceIn(0.2, 0.95)
            prefs[Keys.TARGET_IMAGES] = updated.defaultTargetImages.coerceIn(1, 20)
            prefs[Keys.MAX_CONCURRENT] = updated.maxConcurrentTasks.coerceIn(1, 4)
            prefs[Keys.SEARXNG_URL] = updated.searxngBaseUrl.trim()
            prefs[Keys.ENABLE_SOCIAL] = updated.enableSocialDiscovery
            prefs[Keys.ENABLE_STUDIO] = updated.enableCreativeStudio
            prefs[Keys.AUTO_STOP] = updated.autoStopOnSufficientImages
        }
    }
}
