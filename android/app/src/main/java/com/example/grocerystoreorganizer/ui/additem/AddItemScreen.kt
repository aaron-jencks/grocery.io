package com.example.grocerystoreorganizer.ui.additem

import android.Manifest
import android.app.DatePickerDialog
import android.app.TimePickerDialog
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.clickable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.grocerystoreorganizer.data.local.entity.PackagingStyle
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.data.local.repository.buildVariantLabel
import com.example.grocerystoreorganizer.ui.state.LocationUiState
import com.example.grocerystoreorganizer.ui.state.PhotoUiState
import java.time.LocalDate
import java.time.LocalDateTime

@Composable
fun AddItemScreen(
    prefill: PriceObservationPrefill? = null,
    onObservationSaved: (() -> Unit)? = null,
) {
    val context = LocalContext.current
    val focusManager = LocalFocusManager.current
    val vm: AddGroceryItemViewModel = viewModel(factory = AddGroceryVmFactory(context, prefill))
    val state by vm.state.collectAsState()

    val locationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
        onResult = { granted -> vm.onLocationPermissionResult(granted) }
    )
    val cameraPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
        onResult = { granted -> vm.onCameraPermissionResult(granted) }
    )
    val takePictureLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture(),
        onResult = { success -> vm.onPhotoCaptureResult(success) }
    )

    LaunchedEffect(state.photo) {
        val photoState = state.photo
        when (photoState) {
            PhotoUiState.NeedsPermission -> {
                cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
            }
            is PhotoUiState.LaunchCapture -> {
                vm.onPhotoCaptureLaunched()
                takePictureLauncher.launch(Uri.parse(photoState.outputUri))
            }
            else -> Unit
        }
    }
    LaunchedEffect(state.savedId) {
        if (state.savedId != null && onObservationSaved != null) {
            onObservationSaved()
            vm.clearSavedFlag()
        }
    }

    state.upcConflictMessage?.let { message ->
        AlertDialog(
            onDismissRequest = vm::acknowledgeUpcConflict,
            confirmButton = {
                TextButton(onClick = vm::acknowledgeUpcConflict) {
                    Text("OK")
                }
            },
            title = { Text("UPC Already Exists") },
            text = { Text(message) },
        )
    }
    state.parseDialogMessage?.let { message ->
        AlertDialog(
            onDismissRequest = vm::acknowledgeParseDialog,
            confirmButton = {
                TextButton(onClick = vm::acknowledgeParseDialog) {
                    Text("Continue manual")
                }
            },
            dismissButton = if (state.parseDialogAllowRetry) {
                {
                    TextButton(onClick = vm::retryPhotoFromParseDialog) {
                        Text("Try again")
                    }
                }
            } else {
                null
            },
            title = { Text("Photo Parse Result") },
            text = { Text(message) },
        )
    }

    Column(
        modifier = Modifier
            .statusBarsPadding()
            .padding(16.dp)
            .verticalScroll(rememberScrollState())
            .imePadding()
            .navigationBarsPadding(),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Add Price Observation", style = MaterialTheme.typography.titleLarge)

        Card {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Step 1: UPC", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = state.itemUPC,
                    onValueChange = vm::onUPCChange,
                    label = { Text("UPC*") },
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Number,
                        imeAction = ImeAction.Done,
                    ),
                    keyboardActions = KeyboardActions(
                        onDone = {
                            focusManager.clearFocus(force = true)
                            vm.resolveUpc()
                        }
                    ),
                    singleLine = true,
                    isError = state.upcError != null,
                    modifier = Modifier.fillMaxWidth()
                )
                state.upcError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        onClick = vm::resolveUpc,
                        enabled = !state.isResolvingUpc,
                    ) {
                        Text(if (state.isResolvingUpc) "Checking..." else "Continue")
                    }
                    Button(onClick = vm::requestPhotoCapture) {
                        Text("Take photo")
                    }
                    if (state.upcResolved) {
                        TextButton(onClick = vm::resolveUpc) { Text("Re-check") }
                    }
                }
                if (!state.upcResolved) {
                    TextButton(onClick = vm::continueWithoutUpcForVariableWeight) {
                        Text("No UPC (variable weight)")
                    }
                }
                state.upcLookupMessage?.let {
                    Text(
                        it,
                        color = if (state.requiresProductVariantDetails) {
                            MaterialTheme.colorScheme.error
                        } else {
                            MaterialTheme.colorScheme.primary
                        }
                    )
                }
            }
        }

        if (!state.upcResolved) {
            state.generalError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(24.dp))
            return@Column
        }

        if (state.requiresProductVariantDetails) {
            Card {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Step 2: Product", style = MaterialTheme.typography.titleMedium)
                    OutlinedTextField(
                        value = state.productName,
                        onValueChange = vm::onProductNameChange,
                        label = { Text("Product name*") },
                        isError = state.productError != null,
                        modifier = Modifier.fillMaxWidth()
                    )
                    state.productError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                    Column {
                        HintFieldLabel(
                            label = "Category (optional)",
                            hint = "You can enter multiple categories separated by ';'. Example: Drinks; Soda; Caffeine.",
                        )
                        OutlinedTextField(
                            value = state.productCategory,
                            onValueChange = vm::onProductCategoryChange,
                            label = { Text("Category (optional)") },
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
            }

            Card {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Step 2: Variant", style = MaterialTheme.typography.titleMedium)
                    OutlinedTextField(
                        value = state.brand,
                        onValueChange = vm::onBrandChange,
                        label = { Text("Brand (optional)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = state.flavor,
                        onValueChange = vm::onFlavorChange,
                        label = { Text("Flavor (optional)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    PackagingStyleDropdown(
                        label = "Packaging style (optional)",
                        selected = state.packagingStyle,
                        onSelected = vm::onPackagingStyleChange,
                    )
                    val derivedVariantLabel = buildVariantLabel(
                        brand = state.brand,
                        flavor = state.flavor,
                        packagingStyle = state.packagingStyle,
                        fallback = state.variantLabel,
                    )
                    if (derivedVariantLabel.isNotBlank()) {
                        Text(
                            text = "Variant preview: $derivedVariantLabel",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    state.variantError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Column(modifier = Modifier.weight(1f)) {
                            HintFieldLabel(
                                label = "Pack count*",
                                hint = "How many items are in the package. Example: a 12-pack of soda has pack count 12.",
                            )
                            OutlinedTextField(
                                value = state.packCount,
                                onValueChange = vm::onPackCountChange,
                                label = { Text("Pack count*") },
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                isError = state.packCountError != null,
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                        Column(modifier = Modifier.weight(1f)) {
                            HintFieldLabel(
                                label = "Net quantity*",
                                hint = "The size of each individual item. Example: in a 12-pack of 12 oz cans, quantity is 12 oz.",
                            )
                            OutlinedTextField(
                                value = state.netQuantity,
                                onValueChange = vm::onNetQuantityChange,
                                label = { Text("Net quantity*") },
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                                isError = state.netQuantityError != null,
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                    }
                    state.packCountError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                    state.netQuantityError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                    ProductUnitDropdown(
                        label = "Quantity unit",
                        selected = state.quantityUnit,
                        onSelected = vm::onQuantityUnitChange,
                    )
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = state.isVariableWeight, onCheckedChange = vm::onVariableWeightChange)
                        Text("Variable weight")
                    }
                }
            }
        } else {
            Card {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Matched Product", style = MaterialTheme.typography.titleMedium)
                    Text("Product: ${state.productName}")
                    if (state.productCategory.isNotBlank()) {
                        Text("Category: ${state.productCategory}")
                    }
                    Text("Variant: ${buildVariantLabel(state.brand, state.flavor, state.packagingStyle, state.variantLabel)}")
                    Text("Pack: ${state.packCount}")
                    Text("Net quantity: ${state.netQuantity} ${state.quantityUnit.display}")
                    Text("Variable weight: ${if (state.isVariableWeight) "Yes" else "No"}")
                }
            }
        }

        Card {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Store", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = state.storeName,
                    onValueChange = vm::onStoreNameChange,
                    label = { Text("Store name (optional)") },
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = state.storeAddress,
                    onValueChange = vm::onStoreAddressChange,
                    label = { Text("Store address*") },
                    isError = state.storeAddressError != null,
                    modifier = Modifier.fillMaxWidth()
                )
                state.storeAddressError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = state.storeLatitude,
                        onValueChange = vm::onStoreLatitudeChange,
                        label = { Text("Latitude*") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        isError = state.latitudeError != null,
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedTextField(
                        value = state.storeLongitude,
                        onValueChange = vm::onStoreLongitudeChange,
                        label = { Text("Longitude*") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        isError = state.longitudeError != null,
                        modifier = Modifier.weight(1f)
                    )
                }
                state.latitudeError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                state.longitudeError?.let { Text(it, color = MaterialTheme.colorScheme.error) }

                when (val loc = state.location) {
                    LocationUiState.Idle -> Unit
                    LocationUiState.Loading -> Text("Detecting location...")
                    LocationUiState.NeedsPermission -> {
                        Text("Location permission required.", color = MaterialTheme.colorScheme.error)
                        TextButton(onClick = {
                            locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
                        }) { Text("Grant location permission") }
                    }
                    is LocationUiState.Ready -> Text("Detected: ${loc.address}")
                    is LocationUiState.Error -> Text(loc.message, color = MaterialTheme.colorScheme.error)
                }
                TextButton(onClick = vm::requestLocation) { Text("Use current location") }
            }
        }

        Card {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Observation", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = state.itemPrice,
                    onValueChange = vm::onPriceChange,
                    label = { Text("Price total*") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    isError = state.priceError != null,
                    modifier = Modifier.fillMaxWidth()
                )
                state.priceError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                OutlinedTextField(
                    value = state.observedAt,
                    onValueChange = vm::onObservedAtChange,
                    label = { Text("Observed at (ISO-8601)*") },
                    isError = state.observedAtError != null,
                    modifier = Modifier.fillMaxWidth()
                )
                state.observedAtError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            }
        }

        Card {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Photo (optional)", style = MaterialTheme.typography.titleMedium)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = vm::requestPhotoCapture) {
                        Text("Take photo")
                    }
                    Button(
                        onClick = vm::parseCapturedPhoto,
                        enabled = state.photo is PhotoUiState.Ready && !state.isParsingPhoto,
                    ) {
                        Text(if (state.isParsingPhoto) "Parsing..." else "Parse photo")
                    }
                    if (state.photo is PhotoUiState.Ready) {
                        TextButton(onClick = vm::clearPhoto) { Text("Remove") }
                    }
                }

                when (val p = state.photo) {
                    PhotoUiState.Idle -> Text("Capture a shelf tag or barcode image.")
                    PhotoUiState.NeedsPermission -> {
                        Text("Camera permission required.", color = MaterialTheme.colorScheme.error)
                        TextButton(onClick = {
                            cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
                        }) { Text("Grant camera permission") }
                    }
                    PhotoUiState.Preparing -> Text("Preparing camera...")
                    PhotoUiState.Capturing -> Text("Capturing...")
                    is PhotoUiState.LaunchCapture -> Text("Launching camera...")
                    is PhotoUiState.Ready -> Text("Photo saved: ${p.outputUri}")
                    is PhotoUiState.Error -> Text(p.message, color = MaterialTheme.colorScheme.error)
                }
                if (state.photo is PhotoUiState.Ready) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(
                            checked = state.photoUpcPresent,
                            onCheckedChange = vm::onPhotoUpcPresentChange,
                        )
                        Text("UPC is visible in photo")
                    }
                }
                if (state.isParsingPhoto) {
                    Text("Extracting fields from photo...")
                }
            }
        }

        Card {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = state.isSale, onCheckedChange = vm::onIsSaleChange)
                    Text("Sale price")
                }
                if (state.isSale) {
                    DateTimePickerField(
                        label = "Sale start date*",
                        value = state.saleStartDate,
                        includesTime = state.saleStartIncludesTime,
                        onIncludesTimeChange = vm::onSaleStartIncludesTimeChange,
                        onDatePicked = vm::onSaleStartDatePicked,
                        onTimePicked = vm::onSaleStartTimePicked,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    state.saleStartDateError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                    DateTimePickerField(
                        label = "Sale expiration date (optional)",
                        value = state.saleExpirationDate,
                        includesTime = state.saleExpirationIncludesTime,
                        onIncludesTimeChange = vm::onSaleExpirationIncludesTimeChange,
                        onDatePicked = vm::onSaleExpirationDatePicked,
                        onTimePicked = vm::onSaleExpirationTimePicked,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(
                            value = state.saleMinimumQuantity,
                            onValueChange = vm::onSaleMinimumQuantityChange,
                            label = { Text("Min qty (optional)") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            modifier = Modifier.weight(1f)
                        )
                        OutlinedTextField(
                            value = state.saleLimitQuantity,
                            onValueChange = vm::onSaleLimitQuantityChange,
                            label = { Text("Limit qty (optional)") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
            }
        }

        state.generalError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Button(
            onClick = vm::submit,
            enabled = !state.isSaving,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (state.isSaving) "Saving..." else "Save observation")
        }
        state.savedId?.let { id ->
            Text("Saved observation id=$id")
            TextButton(onClick = vm::clearSavedFlag) { Text("OK") }
        }
        androidx.compose.foundation.layout.Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
private fun HintFieldLabel(
    label: String,
    hint: String,
) {
    var showHint by remember { mutableStateOf(false) }
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(label, style = MaterialTheme.typography.labelMedium)
            HintButton(
                onClick = { showHint = !showHint }
            )
        }
        if (showHint) {
            Text(
                text = hint,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun HintButton(
    onClick: () -> Unit,
) {
    Surface(
        onClick = onClick,
        shape = CircleShape,
        color = MaterialTheme.colorScheme.secondaryContainer,
        contentColor = MaterialTheme.colorScheme.onSecondaryContainer,
    ) {
        Box(
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
            contentAlignment = Alignment.Center,
        ) {
            Text("?", style = MaterialTheme.typography.labelLarge)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ProductUnitDropdown(
    label: String,
    selected: ProductUnit,
    onSelected: (ProductUnit) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = !expanded },
    ) {
        OutlinedTextField(
            value = "${selected.name} (${selected.display})",
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier
                .menuAnchor()
                .fillMaxWidth()
        )
        ExposedDropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
        ) {
            ProductUnit.entries.forEach { unit ->
                DropdownMenuItem(
                    text = { Text("${unit.name} (${unit.display})") },
                    onClick = {
                        onSelected(unit)
                        expanded = false
                    }
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PackagingStyleDropdown(
    label: String,
    selected: PackagingStyle?,
    onSelected: (PackagingStyle?) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = !expanded },
    ) {
        OutlinedTextField(
            value = selected?.display ?: "",
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier
                .menuAnchor()
                .fillMaxWidth()
        )
        ExposedDropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
        ) {
            DropdownMenuItem(
                text = { Text("None") },
                onClick = {
                    onSelected(null)
                    expanded = false
                }
            )
            PackagingStyle.entries.forEach { value ->
                DropdownMenuItem(
                    text = { Text(value.display) },
                    onClick = {
                        onSelected(value)
                        expanded = false
                    }
                )
            }
        }
    }
}

@Composable
private fun DateTimePickerField(
    label: String,
    value: String,
    includesTime: Boolean,
    onIncludesTimeChange: (Boolean) -> Unit,
    onDatePicked: (LocalDate) -> Unit,
    onTimePicked: (Int, Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val parsedDate = remember(value) { parseDisplayDate(value) ?: LocalDate.now() }
    val parsedTime = remember(value) { parseDisplayTime(value) ?: LocalDateTime.now().toLocalTime().withSecond(0).withNano(0) }

    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedTextField(
            value = value,
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            modifier = Modifier
                .fillMaxWidth()
                .clickable {
                    DatePickerDialog(
                        context,
                        { _, year, month, dayOfMonth ->
                            onDatePicked(LocalDate.of(year, month + 1, dayOfMonth))
                        },
                        parsedDate.year,
                        parsedDate.monthValue - 1,
                        parsedDate.dayOfMonth,
                    ).show()
                },
        )
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Checkbox(
                checked = includesTime,
                onCheckedChange = onIncludesTimeChange,
            )
            Text("Include time")
            if (includesTime) {
                TextButton(
                    onClick = {
                        TimePickerDialog(
                            context,
                            { _, hourOfDay, minute -> onTimePicked(hourOfDay, minute) },
                            parsedTime.hour,
                            parsedTime.minute,
                            false,
                        ).show()
                    },
                ) {
                    Text("Set time")
                }
            }
        }
    }
}

private fun parseDisplayDate(value: String): LocalDate? {
    val trimmed = value.trim()
    if (trimmed.isEmpty()) return null
    return runCatching { LocalDate.parse(trimmed.take(10)) }.getOrNull()
}

private fun parseDisplayTime(value: String) =
    runCatching { LocalDateTime.parse(value.trim()).toLocalTime() }.getOrNull()
