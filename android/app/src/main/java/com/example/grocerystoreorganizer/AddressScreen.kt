package com.example.grocerystoreorganizer

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel

@Composable
fun AddressScreen(vm: AddressViewModel = viewModel()) {
    val context = LocalContext.current
    val state by vm.uiState.collectAsState()

    // Helper: check permission any time
    fun hasFineLocationPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
    }

    val permissionLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) {
                vm.refresh(context.applicationContext)
            } else {
                vm.setPermissionDenied()
            }
        }

    fun requestPermissionOrRefresh() {
        if (hasFineLocationPermission()) {
            vm.refresh(context.applicationContext)
        } else {
            vm.setRequestingPermission()
            permissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
        }
    }

    // Kick off once on app open
    LaunchedEffect(Unit) {
        requestPermissionOrRefresh()
    }

    val message = when (val s = state) {
        AddressUiState.Idle -> "Starting…"
        AddressUiState.RequestingPermission -> "Requesting location permission…"
        AddressUiState.LoadingLocation -> "Getting current location…"
        AddressUiState.ReverseGeocoding -> "Reverse geocoding…"
        is AddressUiState.Success -> s.addressLine
        is AddressUiState.Error -> s.message
    }

    val isBusy = state is AddressUiState.LoadingLocation || state is AddressUiState.ReverseGeocoding
    val buttonLabel = when (state) {
        is AddressUiState.Success -> "Refresh"
        is AddressUiState.Error -> "Retry"
        AddressUiState.RequestingPermission -> "Try Again"
        else -> "Retry"
    }

    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(message)
            Spacer(Modifier.height(16.dp))
            Button(
                onClick = { requestPermissionOrRefresh() },
                enabled = !isBusy
            ) {
                Text(buttonLabel)
            }
        }
    }
}
