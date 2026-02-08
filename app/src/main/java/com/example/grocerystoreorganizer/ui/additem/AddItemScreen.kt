package com.example.grocerystoreorganizer.ui.additem

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.grocerystoreorganizer.data.local.entity.GroceryItemQuantifier
import com.example.grocerystoreorganizer.ui.QuantifierRadioRow
import com.example.grocerystoreorganizer.ui.state.LocationUiState
import com.example.grocerystoreorganizer.ui.state.PhotoUiState

@Composable
fun AddItemScreen() {
    val context = LocalContext.current
    val vm: AddGroceryItemViewModel = viewModel(factory = AddGroceryVmFactory(context))
    val state by vm.state.collectAsState()

    val locationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
        onResult = { granted -> vm.onLocationPermissionResult(granted) }
    )

    // If VM says it needs permission, you can auto-trigger or show a button.
    // Here we show a button in the UI instead (less surprising UX).

    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Add Grocery Item", style = MaterialTheme.typography.titleLarge)

        OutlinedTextField(
            value = state.itemName,
            onValueChange = vm::onNameChange,
            label = { Text("Item Name*") },
            isError = state.nameError != null,
            modifier = Modifier.fillMaxWidth()
        )
        state.nameError?.let { Text(it, color = MaterialTheme.colorScheme.error) }

        OutlinedTextField(
            value = state.itemUPC,
            onValueChange = vm::onUPCChange,
            label = { Text("Item UPC*") },
            isError = state.upcError != null,
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
        )
        state.upcError?.let { Text(it, color = MaterialTheme.colorScheme.error) }

        Column() {
            OutlinedTextField(
                value = state.itemPrice,
                onValueChange = vm::onPriceChange,
                label = { Text("Price*") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                isError = state.priceError != null
            )
            QuantifierRadioRow(selected = state.itemQuantifier, onSelected = vm::onQuantifierChange)
        }
        state.priceError?.let { Text(it, color = MaterialTheme.colorScheme.error) }

        // --- Location panel ---
        Card {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Detected store/address", style = MaterialTheme.typography.titleMedium)

                when (val loc = state.location) {
                    LocationUiState.Idle -> Text("Not detected yet.")
                    LocationUiState.Loading -> Text("Detecting location…")
                    LocationUiState.NeedsPermission -> {
                        Text("Location permission required to detect address.")
                        Button(onClick = {
                            locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
                        }) { Text("Grant location permission") }
                    }
                    is LocationUiState.Ready -> Text(loc.address)
                    is LocationUiState.Error -> Text(loc.message, color = MaterialTheme.colorScheme.error)
                }

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = vm::requestLocation) { Text("Detect address") }
                }
            }
        }

        // --- Photo placeholder ---
        Card {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Photo (optional)", style = MaterialTheme.typography.titleMedium)
                Button(
                    onClick = vm::onTakePhotoClicked,
                    enabled = state.photo !is PhotoUiState.Capturing && state.photo !is PhotoUiState.Processing
                ) {
                    Text("Take photo")
                }

                when (val p = state.photo) {
                    PhotoUiState.Idle -> Text("Later: AI will extract fields from photo.")
                    PhotoUiState.Capturing -> Text("Capturing…")
                    PhotoUiState.Processing -> Text("Processing…")
                    is PhotoUiState.Ready -> {
                        Text(p.previewDescription)
                        TextButton(onClick = vm::clearPhoto) { Text("Remove") }
                    }
                    is PhotoUiState.Error -> Text(p.message, color = MaterialTheme.colorScheme.error)
                }
            }
        }

        state.generalError?.let { Text(it, color = MaterialTheme.colorScheme.error) }

        Button(
            onClick = vm::submit,
            enabled = !state.isSaving,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (state.isSaving) "Saving…" else "Submit")
        }

        // Success hook (navigate back / snackbar)
        state.savedId?.let { id ->
            Text("Saved! id=$id")
            TextButton(onClick = vm::clearSavedFlag) { Text("OK") }
        }
    }
}
