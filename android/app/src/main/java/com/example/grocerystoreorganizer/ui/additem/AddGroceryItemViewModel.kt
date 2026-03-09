package com.example.grocerystoreorganizer.ui.additem

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.grocerystoreorganizer.data.local.entity.PackagingStyle
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.data.local.repository.CameraRepository
import com.example.grocerystoreorganizer.data.local.repository.CameraResult
import com.example.grocerystoreorganizer.data.local.repository.LocationRepository
import com.example.grocerystoreorganizer.data.local.repository.LocationResult
import com.example.grocerystoreorganizer.data.local.repository.ParsedPriceTagResult
import com.example.grocerystoreorganizer.data.local.repository.PriceObservationCrudRepository
import com.example.grocerystoreorganizer.data.local.repository.PriceObservationDto
import com.example.grocerystoreorganizer.data.local.repository.SaleDto
import com.example.grocerystoreorganizer.data.local.repository.buildVariantLabel
import com.example.grocerystoreorganizer.data.remote.repository.PriceObservationConflictException
import com.example.grocerystoreorganizer.ui.state.AddItemUiState
import com.example.grocerystoreorganizer.ui.state.LocationUiState
import com.example.grocerystoreorganizer.ui.state.PhotoUiState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import android.net.Uri
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneId

class AddGroceryItemViewModel(
    private val groceryRepo: PriceObservationCrudRepository,
    private val locationRepo: LocationRepository,
    private val cameraRepo: CameraRepository,
    private val locationRequired: Boolean = false,
    prefill: PriceObservationPrefill? = null,
) : ViewModel() {
    private val _state = MutableStateFlow(AddItemUiState(observedAt = nowIsoTimestamp()))
    val state: StateFlow<AddItemUiState> = _state
    private var pendingPhotoUri: String? = null

    init {
        if (prefill != null) {
            update { current ->
                current.copy(
                    productName = sanitizeProductNamePrefill(prefill.productName),
                    productCategory = prefill.productCategory.orEmpty(),
                    brand = prefill.brand.orEmpty(),
                    flavor = prefill.flavor.orEmpty(),
                    packagingStyle = prefill.packagingStyle,
                    variantLabel = buildVariantLabel(prefill.brand, prefill.flavor, prefill.packagingStyle, prefill.variantLabel),
                    itemUPC = prefill.upc.orEmpty(),
                    upcResolved = true,
                    requiresProductVariantDetails = true,
                    packCount = prefill.packCount?.toString() ?: current.packCount,
                    netQuantity = prefill.netQuantity?.toString() ?: current.netQuantity,
                    quantityUnit = prefill.quantityUnit ?: current.quantityUnit,
                    isVariableWeight = prefill.isVariableWeight,
                    upcLookupMessage = "Prefilled from optimized grocery item. Review and submit.",
                )
            }
        }
    }

    fun onStoreNameChange(v: String) = update { it.copy(storeName = v, generalError = null, savedId = null, upcConflictMessage = null) }
    fun onStoreAddressChange(v: String) = update {
        it.copy(storeAddress = v, storeAddressError = null, generalError = null, savedId = null, upcConflictMessage = null)
    }
    fun onStoreLatitudeChange(v: String) = update {
        it.copy(storeLatitude = v, latitudeError = null, generalError = null, savedId = null, upcConflictMessage = null)
    }
    fun onStoreLongitudeChange(v: String) = update {
        it.copy(storeLongitude = v, longitudeError = null, generalError = null, savedId = null, upcConflictMessage = null)
    }
    fun onProductNameChange(v: String) = update {
        it.copy(productName = v, productError = null, generalError = null, savedId = null, upcConflictMessage = null)
    }
    fun onProductCategoryChange(v: String) = update { it.copy(productCategory = v, generalError = null, savedId = null, upcConflictMessage = null) }
    fun onBrandChange(v: String) = update {
        it.copy(brand = v, variantError = null, generalError = null, savedId = null, upcConflictMessage = null)
    }
    fun onFlavorChange(v: String) = update {
        it.copy(flavor = v, variantError = null, generalError = null, savedId = null, upcConflictMessage = null)
    }
    fun onPackagingStyleChange(v: PackagingStyle?) = update {
        it.copy(packagingStyle = v, variantError = null, generalError = null, savedId = null, upcConflictMessage = null)
    }
    fun onUPCChange(v: String) = update {
        val normalized = v.filter { ch -> ch.isDigit() }
        if (it.requiresProductVariantDetails) {
            it.copy(
                itemUPC = normalized,
                upcError = null,
                generalError = null,
                savedId = null,
                upcConflictMessage = null,
                isResolvingUpc = false,
                upcLookupMessage = if (normalized.isBlank()) {
                    if (it.allowMissingUpcForVariableWeight || it.isVariableWeight) {
                        "No UPC provided. Continue entering product and variant details."
                    } else {
                        null
                    }
                } else {
                    "UPC changed. Existing product details were preserved; review and continue."
                },
            )
        } else {
            it.copy(
                itemUPC = normalized,
                upcError = null,
                generalError = null,
                savedId = null,
                upcConflictMessage = null,
                upcResolved = false,
                isResolvingUpc = false,
                allowMissingUpcForVariableWeight = false,
                requiresProductVariantDetails = false,
                upcLookupMessage = null,
                productName = "",
                productCategory = "",
                variantLabel = "",
                brand = "",
                flavor = "",
                packagingStyle = null,
                packCount = "1",
                netQuantity = "",
                quantityUnit = ProductUnit.EA,
                isVariableWeight = false,
            )
        }
    }
    fun onPackCountChange(v: String) = update {
        it.copy(packCount = v, packCountError = null, generalError = null, savedId = null, upcConflictMessage = null)
    }
    fun onNetQuantityChange(v: String) = update {
        it.copy(netQuantity = v, netQuantityError = null, generalError = null, savedId = null, upcConflictMessage = null)
    }
    fun onQuantityUnitChange(v: ProductUnit) = update { it.copy(quantityUnit = v, generalError = null, savedId = null, upcConflictMessage = null) }
    fun onVariableWeightChange(v: Boolean) = update { it.copy(isVariableWeight = v, generalError = null, savedId = null, upcConflictMessage = null) }
    fun onPriceChange(v: String) = update {
        it.copy(itemPrice = v, priceError = null, generalError = null, savedId = null, upcConflictMessage = null)
    }
    fun onObservedAtChange(v: String) = update {
        it.copy(observedAt = v, observedAtError = null, generalError = null, savedId = null, upcConflictMessage = null)
    }
    fun onIsSaleChange(v: Boolean) = update {
        it.copy(
            isSale = v,
            saleStartDateError = null,
            generalError = null,
            savedId = null,
            upcConflictMessage = null,
            saleStartDate = if (v && it.saleStartDate.isBlank()) currentDateOnly() else it.saleStartDate,
            saleStartIncludesTime = if (v) it.saleStartIncludesTime else false,
            saleExpirationIncludesTime = if (v) it.saleExpirationIncludesTime else false,
        )
    }
    fun onSaleStartDateChange(v: String) = update {
        it.copy(saleStartDate = v, saleStartDateError = null, generalError = null, savedId = null, upcConflictMessage = null)
    }
    fun onSaleExpirationDateChange(v: String) = update { it.copy(saleExpirationDate = v, generalError = null, savedId = null, upcConflictMessage = null) }
    fun onSaleStartIncludesTimeChange(v: Boolean) = update {
        it.copy(
            saleStartIncludesTime = v,
            saleStartDate = rewriteDateTimeValue(it.saleStartDate, v),
            generalError = null,
            savedId = null,
            upcConflictMessage = null,
        )
    }
    fun onSaleExpirationIncludesTimeChange(v: Boolean) = update {
        it.copy(
            saleExpirationIncludesTime = v,
            saleExpirationDate = rewriteDateTimeValue(it.saleExpirationDate, v),
            generalError = null,
            savedId = null,
            upcConflictMessage = null,
        )
    }
    fun onSaleStartDatePicked(date: LocalDate) = update {
        val currentDateTime = parseDateTime(it.saleStartDate)
        val nextValue = if (it.saleStartIncludesTime) {
            formatDateTime(date.atTime(currentDateTime?.toLocalTime() ?: DEFAULT_TIME))
        } else {
            formatDateOnly(date)
        }
        it.copy(
            saleStartDate = nextValue,
            saleStartDateError = null,
            generalError = null,
            savedId = null,
            upcConflictMessage = null,
        )
    }
    fun onSaleExpirationDatePicked(date: LocalDate) = update {
        val currentDateTime = parseDateTime(it.saleExpirationDate)
        val nextValue = if (it.saleExpirationIncludesTime) {
            formatDateTime(date.atTime(currentDateTime?.toLocalTime() ?: DEFAULT_TIME))
        } else {
            formatDateOnly(date)
        }
        it.copy(
            saleExpirationDate = nextValue,
            generalError = null,
            savedId = null,
            upcConflictMessage = null,
        )
    }
    fun onSaleStartTimePicked(hour: Int, minute: Int) = update {
        val baseDate = parseDateTime(it.saleStartDate)?.toLocalDate()
            ?: parseDateOnly(it.saleStartDate)
            ?: LocalDate.now()
        it.copy(
            saleStartDate = formatDateTime(baseDate.atTime(hour, minute)),
            saleStartDateError = null,
            generalError = null,
            savedId = null,
            upcConflictMessage = null,
        )
    }
    fun onSaleExpirationTimePicked(hour: Int, minute: Int) = update {
        val baseDate = parseDateTime(it.saleExpirationDate)?.toLocalDate()
            ?: parseDateOnly(it.saleExpirationDate)
            ?: LocalDate.now()
        it.copy(
            saleExpirationDate = formatDateTime(baseDate.atTime(hour, minute)),
            generalError = null,
            savedId = null,
            upcConflictMessage = null,
        )
    }
    fun onSaleMinimumQuantityChange(v: String) = update { it.copy(saleMinimumQuantity = v, generalError = null, savedId = null, upcConflictMessage = null) }
    fun onSaleLimitQuantityChange(v: String) = update { it.copy(saleLimitQuantity = v, generalError = null, savedId = null, upcConflictMessage = null) }

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
        parseCapturedPhoto()
    }

    fun onCameraPermissionResult(granted: Boolean) {
        if (granted) requestPhotoCapture()
        else update { it.copy(photo = PhotoUiState.NeedsPermission) }
    }

    fun clearPhoto() {
        pendingPhotoUri = null
        update { it.copy(photo = PhotoUiState.Idle, isParsingPhoto = false) }
    }

    fun onPhotoUpcPresentChange(value: Boolean) = update {
        it.copy(photoUpcPresent = value)
    }

    fun parseCapturedPhoto() = viewModelScope.launch {
        val s = _state.value
        val photoState = s.photo as? PhotoUiState.Ready ?: run {
            update { it.copy(generalError = "Take a photo first") }
            return@launch
        }
        val imageBytes = cameraRepo.readBytes(photoState.outputUri)
        if (imageBytes == null || imageBytes.isEmpty()) {
            update { it.copy(generalError = "Failed to read captured image") }
            return@launch
        }
        val imageFilename = extractTrainingImageFilename(photoState)

        update {
            it.copy(
                isParsingPhoto = true,
                generalError = null,
                parseDialogMessage = null,
                parseDialogAllowRetry = false,
            )
        }
        runCatching {
            groceryRepo.parsePriceTagImage(
                imageJpeg = imageBytes,
                imageFilename = imageFilename,
            )
        }.onSuccess { parsed ->
            applyParsedPhotoResult(parsed)
        }.onFailure { e ->
            update {
                it.copy(
                    isParsingPhoto = false,
                    generalError = e.message ?: "Failed to parse price-tag image",
                )
            }
        }
    }

    fun resolveUpc() = viewModelScope.launch {
        val s = _state.value
        if (s.isResolvingUpc) return@launch
        if (s.allowMissingUpcForVariableWeight && s.itemUPC.isBlank()) {
            update {
                it.copy(
                    upcResolved = true,
                    requiresProductVariantDetails = true,
                    upcError = null,
                    upcLookupMessage = "No UPC provided. Continue for variable-weight item and enter details manually.",
                )
            }
            return@launch
        }
        val upc = normalizeUpc(s.itemUPC) ?: run {
            update { it.copy(upcError = "Enter a valid barcode (digits only, at least 4 digits)") }
            return@launch
        }
        resolveUpcInternal(upc)
    }

    private suspend fun resolveUpcInternal(upc: String) {
        val current = _state.value
        if (current.isResolvingUpc) return

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
                            brand = known.brand.orEmpty(),
                            flavor = known.flavor.orEmpty(),
                            packagingStyle = known.packagingStyle,
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

        val upc = normalizeUpc(s.itemUPC)
        val allowMissingUpcNow = s.allowMissingUpcForVariableWeight && s.isVariableWeight && s.itemUPC.isBlank()
        if (upc == null && !allowMissingUpcNow) {
            update { it.copy(upcError = "Enter a valid barcode (digits only, at least 4 digits)") }
            return@launch
        }

        val productName = s.productName.trim()
        val brand = normalizeDescriptor(s.brand)
        val flavor = normalizeDescriptor(s.flavor)
        val variantLabel = buildVariantLabel(
            brand = brand,
            flavor = flavor,
            packagingStyle = s.packagingStyle,
            fallback = s.variantLabel,
        ).trim()
        val packCount = parseInt(s.packCount)
        val netQuantity = parseDouble(s.netQuantity)

        if (s.requiresProductVariantDetails) {
            if (productName.isEmpty()) {
                update { it.copy(productError = "Product name is required") }
                return@launch
            }
            if (variantLabel.isEmpty()) {
                update { it.copy(variantError = "Enter at least one of brand, flavor, or packaging style") }
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
            variantLabel = variantLabel,
            brand = brand,
            flavor = flavor,
            packagingStyle = s.packagingStyle,
            upc = upc ?: "",
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
            trainingImageJpeg = extractTrainingImageBytes(s.photo),
            trainingImageFilename = extractTrainingImageFilename(s.photo),
            trainingImageUpcPresent = if (s.photo is PhotoUiState.Ready) s.photoUpcPresent else null,
        )

        update { it.copy(isSaving = true, generalError = null, savedId = null, upcConflictMessage = null, observedAt = observedAt) }
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
                if (e is PriceObservationConflictException) {
                    update {
                        it.copy(
                            isSaving = false,
                            upcConflictMessage = "This product already exists on the server. Please enter the UPC again and retry.",
                            upcResolved = false,
                            allowMissingUpcForVariableWeight = false,
                            requiresProductVariantDetails = false,
                            upcLookupMessage = null,
                            itemUPC = "",
                            productName = "",
                            productCategory = "",
                            variantLabel = "",
                            brand = "",
                            flavor = "",
                            packagingStyle = null,
                            packCount = "1",
                            netQuantity = "",
                            quantityUnit = ProductUnit.EA,
                            isVariableWeight = false,
                        )
                    }
                } else {
                    update { it.copy(isSaving = false, generalError = e.message ?: "Failed to save") }
                }
            }
    }

    fun acknowledgeUpcConflict() {
        if (_state.value.upcConflictMessage != null) {
            update { it.copy(upcConflictMessage = null) }
        }
    }

    fun acknowledgeParseDialog() {
        if (_state.value.parseDialogMessage != null) {
            update { it.copy(parseDialogMessage = null, parseDialogAllowRetry = false) }
        }
    }

    fun retryPhotoFromParseDialog() {
        acknowledgeParseDialog()
        requestPhotoCapture()
    }

    fun continueWithoutUpcForVariableWeight() {
        update {
            it.copy(
                allowMissingUpcForVariableWeight = true,
                upcResolved = true,
                requiresProductVariantDetails = true,
                isVariableWeight = true,
                upcError = null,
                upcLookupMessage = "No UPC available. Continue with variable-weight details and submit.",
            )
        }
    }

    fun clearSavedFlag() {
        if (_state.value.savedId != null) update { it.copy(savedId = null) }
    }

    private fun update(block: (AddItemUiState) -> AddItemUiState) {
        _state.value = block(_state.value)
    }

    private suspend fun applyParsedPhotoResult(parsed: ParsedPriceTagResult) {
        val hasStructuredPricing = parsed.priceTotal != null &&
            parsed.netQuantity != null &&
            parsed.quantityUnit != null &&
            (parsed.packCount != null || parsed.isVariableWeight)

        update {
            it.copy(
                isParsingPhoto = false,
                itemPrice = parsed.priceTotal?.toString() ?: it.itemPrice,
                packCount = parsed.packCount?.toString() ?: it.packCount,
                netQuantity = parsed.netQuantity?.toString() ?: it.netQuantity,
                quantityUnit = parsed.quantityUnit ?: it.quantityUnit,
                isVariableWeight = parsed.isVariableWeight,
                photoUpcPresent = parsed.upcParsable,
            )
        }

        val messages = mutableListOf<String>()
        var allowRetry = false

        val effectiveAmbiguous = parsed.ambiguous && !hasStructuredPricing
        val effectiveUnparsable = parsed.unparsable && !hasStructuredPricing

        if (effectiveAmbiguous) {
            messages += "This image looks ambiguous. Please take a clearer picture or continue with manual entry."
            allowRetry = true
        }
        if (effectiveUnparsable) {
            messages += "The image appears unclear or unusable. You can continue with manual entry."
            allowRetry = true
        }
        if (!parsed.upcParsable && !(hasStructuredPricing && parsed.isVariableWeight)) {
            messages += "UPC could not be parsed from the image. Enter the UPC manually to continue."
        }
        parsed.message?.takeIf { it.isNotBlank() }?.let(messages::add)

        val parsedUpc = normalizeUpc(parsed.upc ?: "")
        if (parsedUpc != null) {
            update { it.copy(itemUPC = parsedUpc, upcError = null) }
            resolveUpcInternal(parsedUpc)
        } else if (hasStructuredPricing && parsed.isVariableWeight) {
            update {
                it.copy(
                    allowMissingUpcForVariableWeight = true,
                    upcResolved = true,
                    requiresProductVariantDetails = true,
                    upcLookupMessage = "No UPC parsed. Continuing in variable-weight mode without UPC.",
                )
            }
            messages += "No UPC was parsed, but pricing was extracted. You can continue without UPC for this variable-weight item."
        }

        if (messages.isNotEmpty()) {
            update {
                it.copy(
                    parseDialogMessage = messages.distinct().joinToString("\n\n"),
                    parseDialogAllowRetry = allowRetry,
                )
            }
        }
    }

    private fun extractTrainingImageBytes(photoState: PhotoUiState): ByteArray? {
        val uri = (photoState as? PhotoUiState.Ready)?.outputUri ?: return null
        return cameraRepo.readBytes(uri)
    }

    private fun extractTrainingImageFilename(photoState: PhotoUiState): String? {
        val uri = (photoState as? PhotoUiState.Ready)?.outputUri ?: return null
        val path = Uri.parse(uri).lastPathSegment ?: return null
        return path.substringAfterLast('/')
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

    private fun currentDateOnly(): String = formatDateOnly(LocalDate.now())

    private fun rewriteDateTimeValue(current: String, includesTime: Boolean): String {
        if (current.isBlank()) {
            return if (includesTime) formatDateTime(LocalDate.now().atTime(DEFAULT_TIME)) else currentDateOnly()
        }
        val asDateTime = parseDateTime(current)
        val asDate = asDateTime?.toLocalDate() ?: parseDateOnly(current) ?: LocalDate.now()
        return if (includesTime) {
            formatDateTime(asDate.atTime(asDateTime?.toLocalTime() ?: DEFAULT_TIME))
        } else {
            formatDateOnly(asDate)
        }
    }

    private fun parseDateOnly(value: String): LocalDate? =
        runCatching { LocalDate.parse(value.trim()) }.getOrNull()

    private fun parseDateTime(value: String): LocalDateTime? {
        val trimmed = value.trim()
        return runCatching { LocalDateTime.parse(trimmed) }.getOrNull()
            ?: runCatching { OffsetDateTime.parse(trimmed).atZoneSameInstant(ZoneId.systemDefault()).toLocalDateTime() }.getOrNull()
    }

    private fun formatDateOnly(date: LocalDate): String = date.toString()

    private fun formatDateTime(dateTime: LocalDateTime): String = dateTime.toString()

    private fun sanitizeProductNamePrefill(value: String): String {
        val normalized = value.trim()
        if (normalized.isEmpty()) return ""
        if (normalized.equals("no product information available", ignoreCase = true)) return ""
        if (normalized.equals("unknown product", ignoreCase = true)) return ""
        return normalized
    }

    private fun normalizeDescriptor(value: String): String? =
        value.trim().lowercase().ifBlank { null }

    private companion object {
        val DEFAULT_TIME = java.time.LocalTime.of(12, 0)
    }
}
