package com.example.grocerystoreorganizer.ui.additem

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.grocerystoreorganizer.data.local.entity.GroceryItemQuantifier
import com.example.grocerystoreorganizer.data.local.repository.GroceryStoreRepository
import com.example.grocerystoreorganizer.data.local.repository.LocationRepository
import com.example.grocerystoreorganizer.data.local.repository.LocationResult
import com.example.grocerystoreorganizer.ui.state.AddItemUiState
import com.example.grocerystoreorganizer.ui.state.LocationUiState
import com.example.grocerystoreorganizer.ui.state.PhotoUiState
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class AddGroceryItemViewModel(
    private val groceryRepo: GroceryStoreRepository,
    private val locationRepo: LocationRepository,
    private val locationRequired: Boolean = true
    ) : ViewModel() {
    private val _state = MutableStateFlow(AddItemUiState())
    val state: StateFlow<AddItemUiState> = _state

    // ----- field updates -----
    fun onNameChange(v: String) = update { it.copy(itemName = v, nameError = null, generalError = null, savedId = null) }
    fun onStoreChange(v: String) = update { it.copy(storeAddress = v, generalError = null, savedId = null) }
    fun onLatitudeChange(v: String) = update { it.copy(storeLatitude = v, generalError = null, savedId = null) }
    fun onLongitudeChange(v: String) = update { it.copy(storeLongitude = v, generalError = null, savedId = null) }
    fun onQuantifierChange(v: GroceryItemQuantifier) = update { it.copy(itemQuantifier = v, generalError = null, savedId = null) }
    fun onPriceChange(v: String) = update { it.copy(itemPrice = v, priceError = null, generalError = null, savedId = null) }
    fun onUPCChange(v: String) = update { it.copy(itemUPC = v, upcError = null, generalError = null, savedId = null) }

    // ----- location flow -----
    fun requestLocation() = viewModelScope.launch {
        update { it.copy(location = LocationUiState.Loading, generalError = null) }

        when (val r = locationRepo.getCurrentAddress()) {
            LocationResult.NoPermission ->
                update { it.copy(location = LocationUiState.NeedsPermission) }

            LocationResult.Unavailable ->
                update { it.copy(location = LocationUiState.Error("Turn on location services / try again.")) }

            LocationResult.NoAddress ->
                update { it.copy(location = LocationUiState.Error("Couldn't resolve an address.")) }

            is LocationResult.Success ->
                update { it.copy(location = LocationUiState.Ready(r.address, r.latitude, r.longitude)) }

            is LocationResult.Error ->
                update { it.copy(location = LocationUiState.Error(r.message)) }
        }
    }

    /** UI calls this after the permission prompt returns. */
    fun onLocationPermissionResult(granted: Boolean) {
        if (granted) requestLocation()
        else update { it.copy(location = LocationUiState.NeedsPermission) }
    }

    // ----- photo placeholder -----
    fun onTakePhotoClicked() {
        update { it.copy(photo = PhotoUiState.Capturing) }

        viewModelScope.launch {
            delay(1_000)
            update {
                it.copy(
                    photo = PhotoUiState.Ready("Photo captured (AI extraction coming soon)")
                )
            }
        }
    }

    fun clearPhoto() = update { it.copy(photo = PhotoUiState.Idle) }

    // ----- submit -----
    fun submit() = viewModelScope.launch {
        val s = _state.value
        if (s.isSaving) return@launch

        // validate name
        val name = s.itemName.trim()
        if (name.isEmpty()) {
            update { it.copy(nameError = "Item name is required") }
            return@launch
        }

        // enforce location requirement
        if (locationRequired && s.location !is LocationUiState.Ready) {
            // Kick off location flow; UI will handle permission prompt if needed.
            requestLocation()
            return@launch
        }

        // parse optional numbers
        val price = parseOptionalDouble(s.itemPrice)?.also { p ->
            if (p < 0.0) {
                update { it.copy(priceError = "Price can't be negative") }
                return@launch
            }
        } ?: run {
            if (s.itemPrice.isNotBlank()) {
                update { it.copy(priceError = "Enter a valid number (e.g., 3.49)") }
                return@launch
            }
            update { it.copy(priceError = "Price is required")}
            return@launch
        }

        val upc = parseOptionalInt(s.itemUPC)?.also { p ->
            if (p < 0) {
                update { it.copy(upcError = "Item UPC can't be negative") }
                return@launch
            }
        } ?: run {
            if (s.itemUPC.isNotBlank()) {
                update { it.copy(upcError = "Enter a valid UPC code") }
                return@launch
            }
            update { it.copy(upcError = "Item UPC is required") }
            return@launch
        }

        val detectedStoreAddress = (s.location as? LocationUiState.Ready)
        if (detectedStoreAddress == null) {
           update { it.copy(generalError = "Store address is required")}
           return@launch
        }

        update { it.copy(isSaving = true, generalError = null, savedId = null) }

        runCatching { groceryRepo.updateOrCreateItem(
            detectedStoreAddress.address, detectedStoreAddress.latitude, detectedStoreAddress.longitude,
            s.itemName, upc, price, s.itemQuantifier
        ) }
            .onSuccess { id ->
                update { AddItemUiState() } // clear form after save
            }
            .onFailure { e ->
                update { it.copy(isSaving = false, generalError = e.message ?: "Failed to save") }
            }
    }

    fun clearSavedFlag() {
        if (_state.value.savedId != null) update { it.copy(savedId = null) }
    }

    // ----- helpers -----
    private fun update(block: (AddItemUiState) -> AddItemUiState) {
        _state.value = block(_state.value)
    }

    private fun parseOptionalDouble(text: String): Double? {
        val t = text.trim()
        if (t.isEmpty()) return null
        return t.replace(',', '.').toDoubleOrNull()
    }

    private fun parseOptionalInt(text: String): Int? {
        val t = text.trim()
        if (t.isEmpty()) return null
        return t.trim(',').toIntOrNull()
    }
}