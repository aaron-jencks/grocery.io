package com.example.grocerystoreorganizer.ui

import androidx.compose.foundation.layout.Row
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import com.example.grocerystoreorganizer.data.local.entity.GroceryItemQuantifier

@Composable
fun QuantifierRadioRow(
    selected: GroceryItemQuantifier,
    onSelected: (GroceryItemQuantifier) -> Unit
) {
    Row {
        GroceryItemQuantifier.entries.forEach { option ->
            Row {
                RadioButton(
                    selected = (option == selected),
                    onClick = { onSelected(option) }
                )
                Text(option.name) // or option.name
            }
        }
    }
}