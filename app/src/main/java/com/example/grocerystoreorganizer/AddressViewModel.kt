package com.example.grocerystoreorganizer

import android.content.Context
import android.location.Geocoder
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import java.util.Locale

sealed interface AddressUiState {
    data object Idle : AddressUiState
    data object RequestingPermission : AddressUiState
    data object LoadingLocation : AddressUiState
    data object ReverseGeocoding : AddressUiState
    data class Success(val addressLine: String) : AddressUiState
    data class Error(val message: String) : AddressUiState
}

class AddressViewModel : ViewModel() {
    private val _uiState = MutableStateFlow<AddressUiState>(AddressUiState.Idle)
    val uiState: StateFlow<AddressUiState> = _uiState.asStateFlow()

    fun setRequestingPermission() {
        _uiState.value = AddressUiState.RequestingPermission
    }

    fun setPermissionDenied() {
        _uiState.value = AddressUiState.Error("Location permission denied")
    }

    fun refresh(appContext: Context) {
        viewModelScope.launch {
            _uiState.value = AddressUiState.LoadingLocation

            val fused = LocationServices.getFusedLocationProviderClient(appContext)
            val token = CancellationTokenSource()

            val location = withTimeoutOrNull<android.location.Location>(10_000) @androidx.annotation.RequiresPermission(
                allOf = [android.Manifest.permission.ACCESS_FINE_LOCATION, android.Manifest.permission.ACCESS_COARSE_LOCATION]
            ) {
                fused.getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, token.token).await()
            }

            if (location == null) {
                _uiState.value = AddressUiState.Error("Could not get a location (timeout/unavailable)")
                return@launch
            }

            _uiState.value = AddressUiState.ReverseGeocoding

            val geocoder = Geocoder(appContext, Locale.getDefault())
            val addresses = withContext(Dispatchers.IO) {
                geocoder.getFromLocation(location.latitude, location.longitude, 1)
            }

            val line = addresses?.firstOrNull()?.getAddressLine(0)
            _uiState.value = if (line == null) {
                AddressUiState.Error("Address not found")
            } else {
                AddressUiState.Success(line)
            }
        }
    }
}
