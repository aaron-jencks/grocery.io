package com.example.grocerystoreorganizer.ui

import androidx.compose.foundation.layout.Row
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit

@Composable
fun QuantifierRadioRow(
    selected: ProductUnit,
    onSelected: (ProductUnit) -> Unit
) {
    Row {
        ProductUnit.entries.forEach { option ->
            Row {
                RadioButton(
                    selected = (option == selected),
                    onClick = { onSelected(option) }
                )
                Text(option.name)
            }
        }
    }
}
