package com.example.grocerystoreorganizer.ui.grocerylist

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.grocerystoreorganizer.data.local.entity.Comparison
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.data.local.entity.ProductVariant

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EditGroceryListItemScreen(
    title: String,
    factory: EditGroceryListItemViewModel.Factory,
    onClose: () -> Unit,
) {
    val vm: EditGroceryListItemViewModel = viewModel(factory = factory)
    val state by vm.state.collectAsStateWithLifecycle()

    LaunchedEffect(state.shouldClose) {
        if (state.shouldClose) {
            onClose()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(title = { Text(title) })
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Card {
                Column(
                    modifier = Modifier.padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Text("Step 1: Product", style = MaterialTheme.typography.titleMedium)
                    ExposedDropdownMenuBox(
                        expanded = state.showSuggestionMenu,
                        onExpandedChange = { expanded ->
                            if (expanded) {
                                vm.showSuggestionMenu()
                            } else {
                                vm.dismissSuggestionMenu()
                            }
                        },
                    ) {
                        OutlinedTextField(
                            value = state.name,
                            onValueChange = vm::onNameChange,
                            label = { Text("Product name*") },
                            isError = state.error != null,
                            trailingIcon = {
                                ExposedDropdownMenuDefaults.TrailingIcon(expanded = state.showSuggestionMenu)
                            },
                            modifier = Modifier
                                .menuAnchor()
                                .fillMaxWidth(),
                            enabled = state.isLoaded && !state.isSaving,
                        )
                        ExposedDropdownMenu(
                            expanded = state.showSuggestionMenu,
                            onDismissRequest = vm::dismissSuggestionMenu,
                        ) {
                            state.suggestions.forEach { product ->
                                DropdownMenuItem(
                                    text = { Text(product.name) },
                                    onClick = { vm.onSuggestionSelected(product) },
                                )
                            }
                            DropdownMenuItem(
                                text = { Text("Use \"${state.name.trim()}\" anyway") },
                                onClick = vm::onUseTypedName,
                            )
                        }
                    }
                    SelectionDropdown(
                        label = "Quantity unit",
                        selectedLabel = "${state.quantityUnit.name} (${state.quantityUnit.display})",
                        options = ProductUnit.entries,
                        optionLabel = { "${it.name} (${it.display})" },
                        onSelected = vm::onQuantityUnitChange,
                    )
                    SelectionDropdown(
                        label = "Comparison mode",
                        selectedLabel = state.comparisonMode.display,
                        options = Comparison.entries,
                        optionLabel = { it.display },
                        onSelected = vm::onComparisonModeChange,
                    )
                }
            }
            state.emptySuggestionMessage?.let {
                Text(
                    text = it,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            Card {
                Column(
                    modifier = Modifier.padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Text("Step 2: Preferred Variant", style = MaterialTheme.typography.titleMedium)
                    if (state.variants.isEmpty()) {
                        Text(
                            "No variants found yet. You can skip this for now and set it later with a price observation.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            style = MaterialTheme.typography.bodyMedium,
                        )
                    } else {
                        VariantDropdown(
                            variants = state.variants,
                            selectedVariantId = state.preferredVariantId,
                            onSelected = vm::onPreferredVariantSelected,
                        )
                    }
                }
            }
            state.error?.let {
                Text(
                    text = it,
                    color = MaterialTheme.colorScheme.error,
                )
            }
            Button(
                onClick = vm::submit,
                enabled = state.isLoaded && !state.isSaving,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (state.isSaving) "Saving..." else "Submit")
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun <T> SelectionDropdown(
    label: String,
    selectedLabel: String,
    options: List<T>,
    optionLabel: (T) -> String,
    onSelected: (T) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = !expanded },
    ) {
        OutlinedTextField(
            value = selectedLabel,
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier
                .menuAnchor()
                .fillMaxWidth(),
        )
        ExposedDropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
        ) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(optionLabel(option)) },
                    onClick = {
                        onSelected(option)
                        expanded = false
                    },
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun VariantDropdown(
    variants: List<ProductVariant>,
    selectedVariantId: Int?,
    onSelected: (Int?) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    val selectedLabel = variants.firstOrNull { it.id == selectedVariantId }?.let(::variantLabel)
        ?: "No preferred variant yet"
    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = !expanded },
    ) {
        OutlinedTextField(
            value = selectedLabel,
            onValueChange = {},
            readOnly = true,
            label = { Text("Preferred variant") },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier
                .menuAnchor()
                .fillMaxWidth(),
        )
        ExposedDropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
        ) {
            DropdownMenuItem(
                text = { Text("No preferred variant yet") },
                onClick = {
                    onSelected(null)
                    expanded = false
                },
            )
            variants.forEach { variant ->
                DropdownMenuItem(
                    text = { Text(variantLabel(variant)) },
                    onClick = {
                        onSelected(variant.id)
                        expanded = false
                    },
                )
            }
        }
    }
}

private fun variantLabel(variant: ProductVariant): String =
    "${variant.label} • ${variant.packCount} x ${variant.netQuantity} ${variant.quantityUnit.display}"
