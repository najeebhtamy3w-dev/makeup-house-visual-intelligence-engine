package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.material3.Surface
import com.example.core.configureAppCheck
import com.example.ui.AppNavigation
import com.example.ui.theme.MakeupHouseTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Configure App Check with launch intent BEFORE Compose UI, ViewModels, or Firebase operations
        if (resources.getIdentifier("google_app_id", "string", packageName) != 0) configureAppCheck(this, intent)

        setContent {
            MakeupHouseTheme {
                Surface {
                    AppNavigation()
                }
            }
        }
    }
}
