package com.example.grocerystoreorganizer.ui.additem

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.data.local.repository.CameraRepository
import com.example.grocerystoreorganizer.data.local.repository.CameraResult
import com.example.grocerystoreorganizer.data.local.repository.LocationRepository
import com.example.grocerystoreorganizer.data.local.repository.LocationResult
import com.example.grocerystoreorganizer.data.local.repository.PriceObservationCrudRepository
import com.example.grocerystoreorganizer.data.local.repository.PriceObservationDto
import com.example.grocerystoreorganizer.data.local.repository.SaleDto
import com.example.grocerystoreorganizer.ui.state.AddItemUiState
import com.example.grocerystoreorganizer.ui.state.LocationUiState
import com.example.grocerystoreorganizer.ui.state.PhotoUiState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class AddGroceryItemViewModel(
    private val groceryRepo: PriceObservationCrudRepository,
    private val locationRepo: LocationRepository,
    private val cameraRepo: CameraRepository,
    private val locationRequired: Boolean = false,
) : ViewModel() {
    private val _state = MutableStateFlow(AddItemUiState(observedAt = nowIsoTimestamp()))
    val state: StateFlow<AddItemUiState> = _state
    private var pendingPhotoUri: String? = null

    fun onStoreNameChange(v: String) = update { it.copy(storeName = v, generalError = null, savedId = null) }
    fun onStoreAddressChange(v: String) = update {
        it.copy(storeAddress = v, storeAddressError = null, generalError = null, savedId = null)
    }
    fun onStoreLatitudeChange(v: String) = update {
        it.copy(storeLatitude = v, latitudeError = null, generalError = null, savedId = null)
    }
    fun onStoreLongitudeChange(v: String) = update {
        it.copy(storeLongitude = v, longitudeError = null, generalError = null, savedId = null)
    }
    fun onProductNameChange(v: String) = update {
        it.copy(productName = v, productError = null, generalError = null, savedId = null)
    }
    fun onProductCategoryChange(v: String) = update { it.copy(productCategory = v, generalError = null, savedId = null) }
    fun onVariantLabelChange(v: String) = update {
        it.copy(variantLabel = v, variantError = null, generalError = null, savedId = null)
    }
    fun onUPCChange(v: String) = update {
        val normalized = v.filter { ch -> ch.isDigit() }
        it.copy(
            itemUPC = normalized,
            upcError = null,
            generalError = null,
            savedId = null,
            upcResolved = false,
            isResolvingUpc = false,
            requiresProductVariantDetails = false,
            upcLookupMessage = null,
            productName = "",
            productCategory = "",
            variantLabel = "",
            packCount = "1",
            netQuantity = "",
            quantityUnit = ProductUnit.EA,
            isVariableWeight = false,
        )
    }
    fun onPackCountChange(v: String) = update {
        it.copy(packCount = v, packCountError = null, generalError = null, savedId = null)
    }
    fun onNetQuantityChange(v: String) = update {
        it.copy(netQuantity = v, netQuantityError = null, generalError = null, savedId = null)
    }
    fun onQuantityUnitChange(v: ProductUnit) = update { it.copy(quantityUnit = v, generalError = null, savedId = null) }
    fun onVariableWeightChange(v: Boolean) = update { it.copy(isVariableWeight = v, generalError = null, savedId = null) }
    fun onPriceChange(v: String) = update {
        it.copy(itemPrice = v, priceError = null, generalError = null, savedId = null)
    }
    fun onObservedAtChange(v: String) = update {
        it.copy(observedAt = v, observedAtError = null, generalError = null, savedId = null)
    }
    fun onIsSaleChange(v: Boolean) = update {
        it.copy(
            isSale = v,
            saleStartDateError = null,
            generalError = null,
            savedId = null,
            saleStartDate = if (v && it.saleStartDate.isBlank()) it.observedAt else it.saleStartDate,
        )
    }
    fun onSaleStartDateChange(v: String) = update {
        it.copy(saleStartDate = v, saleStartDateError = null, generalError = null, savedId = null)
    }
    fun onSaleExpirationDateChange(v: String) = update { it.copy(saleExpirationDate = v, generalError = null, savedId = null) }
    fun onSaleMinimumQuantityChange(v: String) = update { it.copy(saleMinimumQuantity = v, generalError = null, savedId = null) }
    fun onSaleLimitQuantityChange(v: String) = update { it.copy(saleLimitQuantity = v, generalError = null, savedId = null) }

    fun requestPhotoCapture() {
        update { it.copy(photo = PhotoUiState.Preparing, generalError = null) }
        when (val result = cameraRepo.prepareCapture()) {
            CameraResult.NoPermission -> {
                update { it.copy(photo = PhotoUiState.NeedsPermission) }
            }

            is CameraResult.Error -> {
                update { it.copy(photo = PhotoUiState.Error(result.message)) }
            }

            is CameraResult.Ready -> {
                pendingPhotoUri = result.outputUri
                update { it.copy(photo = PhotoUiState.LaunchCapture(result.outputUri)) }
            }
        }
    }

    fun onPhotoCaptureLaunched() {
        if (_state.value.photo is PhotoUiState.LaunchCapture) {
            update { it.copy(photo = PhotoUiState.Capturing) }
        }
    }

    fun onPhotoCaptureResult(success: Boolean) {
        val uri = pendingPhotoUri
        if (!success || uri == null) {
            pendingPhotoUri = null
            update { it.copy(photo = PhotoUiState.Error("Photo capture canceled")) }
            return
        }
        update { it.copy(photo = PhotoUiState.Ready(uri)) }
    }

    fun onCameraPermissionResult(granted: Boolean) {
        if (granted) requestPhotoCapture()
        else update { it.copy(photo = PhotoUiState.NeedsPermission) }
    }

    fun clearPhoto() {
        pendingPhotoUri = null
        update { it.copy(photo = PhotoUiState.Idle) }
    }

    fun resolveUpc() = viewModelScope.launch {
        val s = _state.value
        if (s.isResolvingUpc) return@launch
        val upc = normalizeUpc(s.itemUPC) ?: run {
            update { it.copy(upcError = "Enter a valid barcode (digits only, at least 4 digits)") }
            return@launch
        }

        update {
            it.copy(
                isResolvingUpc = true,
                upcError = null,
                generalError = null,
                upcLookupMessage = null,
            )
        }

        runCatching { groceryRepo.getKnownVariantByUpc(upc) }
            .onSuccess { known ->
                if (known == null) {
                    update {
                        it.copy(
                            isResolvingUpc = false,
                            upcResolved = true,
                            requiresProductVariantDetails = true,
                            upcLookupMessage = "UPC not found. Enter product and variant details.",
                        )
                    }
                } else {
                    update {
                        it.copy(
                            isResolvingUpc = false,
                            upcResolved = true,
                            requiresProductVariantDetails = false,
                            upcLookupMessage = "UPC matched an existing product.",
                            productName = known.productName,
                            productCategory = known.productCategory.orEmpty(),
                            variantLabel = known.variantLabel,
                            packCount = known.packCount.toString(),
                            netQuantity = known.netQuantity.toString(),
                            quantityUnit = known.quantityUnit,
                            isVariableWeight = known.isVariableWeight,
                        )
                    }
                }
            }
            .onFailure { e ->
                update {
                    it.copy(
                        isResolvingUpc = false,
                        upcResolved = false,
                        requiresProductVariantDetails = false,
                        upcLookupMessage = null,
                        generalError = e.message ?: "Failed to resolve UPC",
                    )
                }
            }
    }

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
                update {
                    it.copy(
                        location = LocationUiState.Ready(r.address, r.latitude, r.longitude),
                        storeAddress = r.address,
                        storeLatitude = r.latitude.toString(),
                        storeLongitude = r.longitude.toString(),
                        storeAddressError = null,
                        latitudeError = null,
                        longitudeError = null,
                    )
                }

            is LocationResult.Error ->
                update { it.copy(location = LocationUiState.Error(r.message)) }
        }
    }

    fun onLocationPermissionResult(granted: Boolean) {
        if (granted) requestLocation()
        else update { it.copy(location = LocationUiState.NeedsPermission) }
    }

    fun submit() = viewModelScope.launch {
        val s = _state.value
        if (s.isSaving) return@launch

        if (!s.upcResolved) {
            update { it.copy(upcError = "Resolve UPC before continuing") }
            return@launch
        }

        val address = s.storeAddress.trim()
        if (address.isEmpty()) {
            update { it.copy(storeAddressError = "Store address is required") }
            return@launch
        }

        val lat = parseDouble(s.storeLatitude) ?: run {
            update { it.copy(latitudeError = "Valid latitude is required") }
            return@launch
        }
        val lon = parseDouble(s.storeLongitude) ?: run {
            update { it.copy(longitudeError = "Valid longitude is required") }
            return@launch
        }

        val upc = normalizeUpc(s.itemUPC) ?: run {
            update { it.copy(upcError = "Enter a valid barcode (digits only, at least 4 digits)") }
            return@launch
        }

        val productName = s.productName.trim()
        val variantLabel = s.variantLabel.trim()
        val packCount = parseInt(s.packCount)
        val netQuantity = parseDouble(s.netQuantity)

        if (s.requiresProductVariantDetails) {
            if (productName.isEmpty()) {
                update { it.copy(productError = "Product name is required") }
                return@launch
            }
            if (variantLabel.isEmpty()) {
                update { it.copy(variantError = "Variant label is required") }
                return@launch
            }
            if (packCount == null) {
                update { it.copy(packCountError = "Enter a valid pack count") }
                return@launch
            }
            if (packCount <= 0) {
                update { it.copy(packCountError = "Pack count must be greater than zero") }
                return@launch
            }
            if (netQuantity == null) {
                update { it.copy(netQuantityError = "Enter a valid net quantity") }
                return@launch
            }
            if (netQuantity <= 0.0) {
                update { it.copy(netQuantityError = "Net quantity must be greater than zero") }
                return@launch
            }
        } else {
            if (productName.isEmpty() || variantLabel.isEmpty() || packCount == null || netQuantity == null) {
                update { it.copy(generalError = "UPC data is incomplete. Re-check the UPC.") }
                return@launch
            }
        }

        val price = parseDouble(s.itemPrice) ?: run {
            update { it.copy(priceError = "Enter a valid price") }
            return@launch
        }
        if (price < 0.0) {
            update { it.copy(priceError = "Price can't be negative") }
            return@launch
        }

        val observedAt = s.observedAt.trim().ifBlank { nowIsoTimestamp() }
        if (observedAt.isEmpty()) {
            update { it.copy(observedAtError = "Observation time is required") }
            return@launch
        }

        if (locationRequired && s.location !is LocationUiState.Ready) {
            requestLocation()
            return@launch
        }

        val saleStartDate = if (s.isSale) s.saleStartDate.trim().ifBlank { observedAt } else ""
        if (s.isSale && saleStartDate.isBlank()) {
            update { it.copy(saleStartDateError = "Sale start date is required when sale is enabled") }
            return@launch
        }

        val saleMin = parseOptionalInt(s.saleMinimumQuantity)
        val saleLimit = parseOptionalInt(s.saleLimitQuantity)
        if (saleMin != null && saleMin < 0) {
            update { it.copy(generalError = "Sale minimum quantity must be non-negative") }
            return@launch
        }
        if (saleLimit != null && saleLimit < 0) {
            update { it.copy(generalError = "Sale limit quantity must be non-negative") }
            return@launch
        }

        val dto = PriceObservationDto(
            storeAddress = address,
            storeLatitude = lat,
            storeLongitude = lon,
            storeName = s.storeName.trim().ifBlank { null },
            productName = productName,
            productCategory = s.productCategory.trim().ifBlank { null },
            defaultCompareUnit = s.quantityUnit,
            variantLabel = variantLabel,
            upc = upc,
            packCount = packCount,
            netQuantity = netQuantity,
            quantityUnit = s.quantityUnit,
            isVariableWeight = s.isVariableWeight,
            priceTotal = price,
            observedAt = observedAt,
            isSale = s.isSale,
            sale = if (s.isSale) {
                SaleDto(
                    startDate = saleStartDate,
                    expirationDate = s.saleExpirationDate.trim().ifBlank { null },
                    minimumQuantity = saleMin,
                    limitQuantity = saleLimit,
                )
            } else {
                null
            },
        )

        update { it.copy(isSaving = true, generalError = null, savedId = null, observedAt = observedAt) }
        runCatching { groceryRepo.insertPriceObservation(dto) }
            .onSuccess { id ->
                update {
                    AddItemUiState(
                        observedAt = nowIsoTimestamp(),
                        location = it.location,
                        savedId = id,
                    )
                }
            }
            .onFailure { e ->
                update { it.copy(isSaving = false, generalError = e.message ?: "Failed to save") }
            }
    }

    fun clearSavedFlag() {
        if (_state.value.savedId != null) update { it.copy(savedId = null) }
    }

    private fun update(block: (AddItemUiState) -> AddItemUiState) {
        _state.value = block(_state.value)
    }

    private fun parseDouble(text: String): Double? =
        text.trim().replace(',', '.').toDoubleOrNull()

    private fun parseInt(text: String): Int? =
        text.trim().toIntOrNull()

    private fun normalizeUpc(text: String): String? {
        val t = text.trim()
        if (t.length < 4) return null
        if (!t.all { it.isDigit() }) return null
        return t
    }

    private fun parseOptionalInt(text: String): Int? {
        val t = text.trim()
        if (t.isEmpty()) return null
        return t.toIntOrNull()
    }

    private fun nowIsoTimestamp(): String =
        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX", Locale.US).format(Date())
}
