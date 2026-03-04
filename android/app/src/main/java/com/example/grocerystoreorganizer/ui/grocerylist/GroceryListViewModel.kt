package com.example.grocerystoreorganizer.ui.grocerylist

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.grocerystoreorganizer.data.local.repository.LocalGroceryListItem
import com.example.grocerystoreorganizer.data.local.repository.LocalGroceryListRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class GroceryListViewModel(
    private val repository: LocalGroceryListRepository,
) : ViewModel() {
    val items: StateFlow<List<LocalGroceryListItem>> = repository.observeItems()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    fun deleteItem(id: Int) {
        viewModelScope.launch {
            repository.deleteItem(id)
        }
    }

    fun moveItem(fromIndex: Int, toIndex: Int) {
        viewModelScope.launch {
            repository.moveItem(fromIndex, toIndex)
        }
    }

    fun incrementDesiredCount(id: Int) {
        viewModelScope.launch {
            repository.incrementDesiredCount(id)
        }
    }

    fun decrementDesiredCount(id: Int) {
        viewModelScope.launch {
            repository.decrementDesiredCount(id)
        }
    }

    fun clearError() {
        _error.value = null
    }

    class Factory(
        private val repository: LocalGroceryListRepository,
    ) : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            @Suppress("UNCHECKED_CAST")
            return GroceryListViewModel(repository) as T
        }
    }
}
