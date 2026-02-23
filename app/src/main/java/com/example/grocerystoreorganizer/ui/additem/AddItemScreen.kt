package com.example.grocerystoreorganizer.ui.additem

import android.Manifest
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.ui.state.LocationUiState
import com.example.grocerystoreorganizer.ui.state.PhotoUiState

@Composable
fun AddItemScreen() {
    val context = LocalContext.current
    val focusManager = LocalFocusManager.current
    val vm: AddGroceryItemViewModel = viewModel(factory = AddGroceryVmFactory(context))
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
                    OutlinedTextField(
                        value = state.productCategory,
                        onValueChange = vm::onProductCategoryChange,
                        label = { Text("Category (optional)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }

            Card {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Step 2: Variant", style = MaterialTheme.typography.titleMedium)
                    OutlinedTextField(
                        value = state.variantLabel,
                        onValueChange = vm::onVariantLabelChange,
                        label = { Text("Variant label*") },
                        isError = state.variantError != null,
                        modifier = Modifier.fillMaxWidth()
                    )
                    state.variantError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(
                            value = state.packCount,
                            onValueChange = vm::onPackCountChange,
                            label = { Text("Pack count*") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            isError = state.packCountError != null,
                            modifier = Modifier.weight(1f)
                        )
                        OutlinedTextField(
                            value = state.netQuantity,
                            onValueChange = vm::onNetQuantityChange,
                            label = { Text("Net quantity*") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                            isError = state.netQuantityError != null,
                            modifier = Modifier.weight(1f)
                        )
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
                    Text("Variant: ${state.variantLabel}")
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
            }
        }

        Card {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = state.isSale, onCheckedChange = vm::onIsSaleChange)
                    Text("Sale price")
                }
                if (state.isSale) {
                    OutlinedTextField(
                        value = state.saleStartDate,
                        onValueChange = vm::onSaleStartDateChange,
                        label = { Text("Sale start date (ISO-8601)*") },
                        isError = state.saleStartDateError != null,
                        modifier = Modifier.fillMaxWidth()
                    )
                    state.saleStartDateError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                    OutlinedTextField(
                        value = state.saleExpirationDate,
                        onValueChange = vm::onSaleExpirationDateChange,
                        label = { Text("Sale expiration date (optional)") },
                        modifier = Modifier.fillMaxWidth()
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
private fun ProductUnitDropdown(
    label: String,
    selected: ProductUnit,
    onSelected: (ProductUnit) -> Unit,
) {
    val entries = ProductUnit.entries
    val selectedIndex = entries.indexOf(selected).coerceAtLeast(0)
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        OutlinedTextField(
            value = "${selected.name} (${selected.display})",
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            modifier = Modifier.fillMaxWidth()
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            TextButton(onClick = {
                val prev = if (selectedIndex == 0) entries.last() else entries[selectedIndex - 1]
                onSelected(prev)
            }) { Text("Prev") }
            TextButton(onClick = {
                val next = if (selectedIndex == entries.lastIndex) entries.first() else entries[selectedIndex + 1]
                onSelected(next)
            }) { Text("Next") }
        }
    }
}
