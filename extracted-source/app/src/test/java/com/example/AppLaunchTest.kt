package com.example

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.LooperMode

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
@LooperMode(LooperMode.Mode.PAUSED)
class AppLaunchTest {
    @get:Rule val compose = createAndroidComposeRule<MainActivity>()
    @Test fun localWorkspaceLaunchesWithoutFirebaseAndNavigationWorks() {
        compose.onNodeWithText("MH-VIE").assertIsDisplayed()
        compose.onNodeWithText("المزيد").performClick()
        compose.onNodeWithText("محرك MH-VIE الخاص بك").assertIsDisplayed()
    }
}
