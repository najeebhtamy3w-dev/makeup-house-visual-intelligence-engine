package com.example.ui

import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AddBox
import androidx.compose.material.icons.filled.Collections
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.PlayCircle
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.Storefront
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.credentials.CredentialManager
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.model.UiState
import com.google.firebase.Firebase
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseUser
import com.google.firebase.auth.auth
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow

const val ROUTE_DASHBOARD = "dashboard"
const val ROUTE_NEW_BATCH = "new_batch"
const val ROUTE_MONITOR = "monitor"
const val ROUTE_GALLERY = "gallery"
const val ROUTE_ZERO_RESULTS = "zero_results"
const val ROUTE_BRANDS = "brands"
const val ROUTE_ENGINES = "engines"
const val ROUTE_SETTINGS = "settings"
const val ROUTE_PRODUCT_DETAIL = "product_detail/{productId}"

data class TopDest(val route: String, val label: String, val icon: ImageVector)

private val PrimaryDestinations = listOf(
    TopDest(ROUTE_DASHBOARD, "الرئيسية", Icons.Default.Dashboard),
    TopDest(ROUTE_NEW_BATCH, "دفعة", Icons.Default.AddBox),
    TopDest(ROUTE_MONITOR, "التنفيذ", Icons.Default.PlayCircle),
    TopDest(ROUTE_GALLERY, "المعرض", Icons.Default.Collections),
    TopDest(ROUTE_SETTINGS, "المزيد", Icons.Default.Settings)
)

private val RailDestinations = listOf(
    TopDest(ROUTE_DASHBOARD, "الرئيسية", Icons.Default.Dashboard),
    TopDest(ROUTE_NEW_BATCH, "إضافة دفعة", Icons.Default.AddBox),
    TopDest(ROUTE_MONITOR, "متابعة التنفيذ", Icons.Default.PlayCircle),
    TopDest(ROUTE_GALLERY, "المعرض البصري", Icons.Default.Collections),
    TopDest(ROUTE_ZERO_RESULTS, "النتيجة صفر", Icons.Default.ErrorOutline),
    TopDest(ROUTE_BRANDS, "الماركات", Icons.Default.Storefront),
    TopDest(ROUTE_ENGINES, "المحركات", Icons.Default.Speed),
    TopDest(ROUTE_SETTINGS, "الإعدادات", Icons.Default.Settings)
)

internal fun FirebaseAuth.authStateFlow(): Flow<FirebaseUser?> = callbackFlow {
    val listener = FirebaseAuth.AuthStateListener { auth ->
        trySend(auth.currentUser)
    }
    addAuthStateListener(listener)
    awaitClose { removeAuthStateListener(listener) }
}

@Composable
fun AppNavigation(auth: FirebaseAuth? = null) {
    if (auth == null) {
        CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
            AuthenticatedAppShell(currentUserId = "local_workspace", userEmail = "مساحة العمل المحلية")
        }
        return
    }
    val currentUser by auth.authStateFlow().collectAsStateWithLifecycle(initialValue = auth.currentUser)
    val user = currentUser

    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
        if (user == null) {
            AuthScreen(onAuthSuccess = {})
        } else {
            key(user.uid) {
                AuthenticatedAppShell(
                    currentUserId = user.uid,
                    userEmail = user.email
                )
            }
        }
    }
}

@Composable
private fun AuthenticatedAppShell(
    currentUserId: String,
    userEmail: String?
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val credentialManager = remember { CredentialManager.create(context) }

    val viewModel: MhvieViewModel = viewModel(
        key = currentUserId,
        factory = MhvieViewModel.provideFactory(currentUserId)
    )

    val batchesState by viewModel.batchesState.collectAsStateWithLifecycle()
    val productsState by viewModel.productsState.collectAsStateWithLifecycle()
    val brandsState by viewModel.brandsState.collectAsStateWithLifecycle()
    val enginesState by viewModel.enginesState.collectAsStateWithLifecycle()
    val logsState by viewModel.logsState.collectAsStateWithLifecycle()
    val selectedCandidatesState by viewModel.selectedCandidatesState.collectAsStateWithLifecycle()
    val selectedBatchId by viewModel.selectedBatchId.collectAsStateWithLifecycle()
    val orchestratorProgress by viewModel.orchestratorProgress.collectAsStateWithLifecycle()
    val settings by viewModel.settings.collectAsStateWithLifecycle()
    val studioState by viewModel.studioState.collectAsStateWithLifecycle()
    val isBenchmarking by viewModel.isBenchmarking.collectAsStateWithLifecycle()
    val snackbarMessage by viewModel.snackbarMessage.collectAsStateWithLifecycle()

    val snackbarHostState = remember { SnackbarHostState() }
    LaunchedEffect(snackbarMessage) {
        val msg = snackbarMessage
        if (!msg.isNullOrBlank()) {
            snackbarHostState.showSnackbar(msg)
            viewModel.clearSnackbar()
        }
    }

    val navController = rememberNavController()
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    fun navigateTop(route: String) {
        navController.navigate(route) {
            popUpTo(navController.graph.findStartDestination().id) { saveState = true }
            launchSingleTop = true
            restoreState = true
        }
    }

    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        val isWideScreen = maxWidth >= 600.dp

        Scaffold(
            contentWindowInsets = WindowInsets.safeDrawing,
            snackbarHost = { SnackbarHost(snackbarHostState) },
            bottomBar = {
                if (!isWideScreen && currentRoute?.startsWith("product_detail") != true) {
                    NavigationBar {
                        PrimaryDestinations.forEach { dest ->
                            NavigationBarItem(
                                selected = currentRoute == dest.route,
                                onClick = { navigateTop(dest.route) },
                                icon = { Icon(dest.icon, contentDescription = dest.label) },
                                label = { Text(dest.label) }
                            )
                        }
                    }
                }
            }
        ) { innerPadding ->
            Row(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
            ) {
                if (isWideScreen) {
                    NavigationRail {
                        RailDestinations.forEach { dest ->
                            NavigationRailItem(
                                selected = currentRoute == dest.route,
                                onClick = { navigateTop(dest.route) },
                                icon = { Icon(dest.icon, contentDescription = dest.label) },
                                label = { Text(dest.label) }
                            )
                        }
                    }
                }

                NavHost(
                    navController = navController,
                    startDestination = ROUTE_DASHBOARD,
                    modifier = Modifier.weight(1f)
                ) {
                    composable(ROUTE_DASHBOARD) {
                        HomeDashboardScreen(
                            batchesState = batchesState,
                            productsState = productsState,
                            enginesState = enginesState,
                            orchestratorProgress = orchestratorProgress,
                            onNavigateNewBatch = { navigateTop(ROUTE_NEW_BATCH) },
                            onOpenBatchMonitor = { batchId ->
                                viewModel.selectBatch(batchId)
                                navigateTop(ROUTE_MONITOR)
                            },
                            onOpenEngines = { navigateTop(ROUTE_ENGINES) },
                            onOpenZeroResults = { navigateTop(ROUTE_ZERO_RESULTS) }
                        )
                    }

                    composable(ROUTE_NEW_BATCH) {
                        NewBatchScreen(
                            defaultTargetImages = settings.defaultTargetImages,
                            onStartBatchFromPhotos = { title, uris, single, csv, strategy, target ->
                                viewModel.createAndStartBatchFromPhotos(
                                    title, uris, single, csv, strategy, target
                                ) { navigateTop(ROUTE_MONITOR) }
                            },
                            onStartBatchFromZip = { title, zipUri, csv, strategy, target ->
                                viewModel.createAndStartBatchFromZip(
                                    title, zipUri, csv, strategy, target
                                ) { navigateTop(ROUTE_MONITOR) }
                            }
                        )
                    }

                    composable(ROUTE_MONITOR) {
                        BatchMonitorScreen(
                            batchesState = batchesState,
                            productsState = productsState,
                            selectedBatchId = selectedBatchId,
                            orchestratorProgress = orchestratorProgress,
                            onSelectBatch = { viewModel.selectBatch(it) },
                            onPauseBatch = { viewModel.pauseBatch() },
                            onResumeBatch = { viewModel.resumeBatch(it) },
                            onRetryFailed = { viewModel.retryZeroOrFailedInBatch(it) },
                            onExportBatch = { batch, fmt -> viewModel.exportBatch(batch, fmt) },
                            onCancelBatch = { viewModel.cancelBatch(it) },
                            onOpenProduct = { pid ->
                                viewModel.selectProduct(pid)
                                navController.navigate("product_detail/$pid")
                            }
                        )
                    }

                    composable(ROUTE_GALLERY) {
                        GalleryScreen(
                            productsState = productsState,
                            onOpenProduct = { pid ->
                                viewModel.selectProduct(pid)
                                navController.navigate("product_detail/$pid")
                            },
                            onBatchApprove = { ids -> viewModel.batchApproveProducts(ids) }
                        )
                    }

                    composable(ROUTE_ZERO_RESULTS) {
                        ZeroResultScreen(
                            productsState = productsState,
                            onOpenProduct = { pid ->
                                viewModel.selectProduct(pid)
                                navController.navigate("product_detail/$pid")
                            },
                            onReprocess = { viewModel.reprocessProduct(it) },
                            onSendToStudio = { prod ->
                                viewModel.selectProduct(prod.id)
                                navController.navigate("product_detail/${prod.id}")
                            }
                        )
                    }

                    composable(ROUTE_BRANDS) {
                        BrandLibraryScreen(
                            brandsState = brandsState,
                            onUpsertBrand = { viewModel.upsertBrand(it) }
                        )
                    }

                    composable(ROUTE_ENGINES) {
                        EngineManagerScreen(
                            enginesState = enginesState,
                            isBenchmarking = isBenchmarking,
                            onToggleEngine = { eng, enabled -> viewModel.toggleEngine(eng, enabled) },
                            onUpdateEndpoint = { eng, url -> viewModel.updateSearxngEndpoint(eng, url) },
                            onRunBenchmarks = { viewModel.runLiveEngineBenchmarks() }
                        )
                    }

                    composable(ROUTE_SETTINGS) {
                        SettingsAndExportScreen(
                            settings = settings,
                            logsState = logsState,
                            userEmail = userEmail,
                            onUpdateSettings = { viewModel.updateSettings(it) },
                            onExportBackup = { viewModel.exportKnowledgeBaseBackup() },
                            onRestoreBackup = { viewModel.restoreKnowledgeBaseBackup(it) },
                            onOpenBrands = { navigateTop(ROUTE_BRANDS) },
                            onOpenEngines = { navigateTop(ROUTE_ENGINES) },
                            onOpenZeroResults = { navigateTop(ROUTE_ZERO_RESULTS) },
                            onSignOut = { viewModel.clearSnackbar() },
                            backendEndpoint = viewModel.backendEndpoint.collectAsStateWithLifecycle().value,
                            onSaveBackend = { endpoint, token -> viewModel.updateBackendConnection(endpoint, token) }
                        )
                    }

                    composable(
                        route = ROUTE_PRODUCT_DETAIL,
                        arguments = listOf(navArgument("productId") { type = NavType.StringType })
                    ) { entry ->
                        val pid = entry.arguments?.getString("productId").orEmpty()
                        LaunchedEffect(pid) { viewModel.selectProduct(pid) }
                        val allProducts = (productsState as? UiState.Success)?.data.orEmpty()
                        val prod = allProducts.firstOrNull { it.id == pid }
                        ProductDetailScreen(
                            product = prod,
                            candidatesState = selectedCandidatesState,
                            studioState = studioState,
                            onBack = { navController.popBackStack() },
                            onReprocess = { viewModel.reprocessProduct(it) },
                            onApproveCandidate = { p, c -> viewModel.approveCandidate(p, c) },
                            onRejectCandidate = { pId, cId -> viewModel.rejectCandidate(pId, cId) },
                            onDownloadCandidate = { pId, c -> viewModel.downloadCandidateLocally(pId, c) },
                            onGenerateStudio = { p, preset -> viewModel.generateCreativeStudioImage(p, preset) },
                            onSaveIdentity = { viewModel.saveManualIdentity(it) },
                            onReadBarcode = { viewModel.readBarcode(it) },
                            onShareStudio = { viewModel.shareStudio(it) }
                        )
                    }
                }
            }
        }
    }
}
