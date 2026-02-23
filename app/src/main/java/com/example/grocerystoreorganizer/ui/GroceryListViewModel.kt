package com.example.grocerystoreorganizer.ui

import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

sealed interface GroceryListUiState {
    data object Idle : GroceryListUiState
    data object AddingItem : GroceryListUiState
    data object FindingItem : GroceryListUiState
    data object FindingStore : GroceryListUiState
    data class ItemSuccess(val upc: Int) : GroceryListUiState
    data class ItemFailure(val message: String) : GroceryListUiState
}

class GroceryListViewModel : ViewModel() {
    private val _uiState = MutableStateFlow<GroceryListUiState>(GroceryListUiState.Idle)
    val uiState: StateFlow<GroceryListUiState> = _uiState.asStateFlow()

    private var _currentItem: Int? = null

    fun addNewItem(upc: Int) {
        _currentItem = upc
        _uiState.value = GroceryListUiState.AddingItem
    }
}
