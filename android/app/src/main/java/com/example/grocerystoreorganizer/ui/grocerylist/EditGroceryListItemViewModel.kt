package com.example.grocerystoreorganizer.ui.grocerylist

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.grocerystoreorganizer.data.local.entity.Comparison
import com.example.grocerystoreorganizer.data.local.repository.LocalGroceryListRepository
import com.example.grocerystoreorganizer.data.local.repository.ProductCatalogRepository
import com.example.grocerystoreorganizer.data.local.entity.Product
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.data.local.entity.ProductVariant
import com.example.grocerystoreorganizer.data.remote.repository.ProductVariantCatalogRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class EditGroceryListItemUiState(
    val name: String = "",
    val quantityUnit: ProductUnit = ProductUnit.EA,
    val comparisonMode: Comparison = Comparison.cheapestPrice,
    val variants: List<ProductVariant> = emptyList(),
    val preferredVariantId: Int? = null,
    val suggestions: List<Product> = emptyList(),
    val showSuggestionMenu: Boolean = false,
    val emptySuggestionMessage: String? = null,
    val error: String? = null,
    val isSaving: Boolean = false,
    val isLoaded: Boolean = false,
    val shouldClose: Boolean = false,
)

class EditGroceryListItemViewModel(
    private val repository: LocalGroceryListRepository,
    private val productCatalogRepository: ProductCatalogRepository,
    private val variantCatalogRepository: ProductVariantCatalogRepository,
    private val itemId: Int?,
) : ViewModel() {
    private val _state = MutableStateFlow(EditGroceryListItemUiState(isLoaded = itemId == null))
    val state: StateFlow<EditGroceryListItemUiState> = _state.asStateFlow()
    private var matchedProductId: Int? = null

    init {
        if (itemId != null) {
            viewModelScope.launch {
                val item = repository.getItem(itemId)
                _state.value = if (item == null) {
                    EditGroceryListItemUiState(
                        error = "Item not found",
                        isLoaded = true,
                    )
                } else {
                    val product = repository.getProduct(item.productId)
                    matchedProductId = item.productId
                    val variants = repository.getVariantsForProduct(item.productId)
                    EditGroceryListItemUiState(
                        name = product?.name.orEmpty(),
                        quantityUnit = item.quantityUnit,
                        comparisonMode = item.comparisonMode,
                        variants = variants,
                        preferredVariantId = item.preferredVariantId,
                        isLoaded = true,
                    )
                }
            }
        }
    }

    fun onNameChange(value: String) {
        _state.value = _state.value.copy(name = value, error = null)
        refreshSuggestions(value)
        refreshVariants(value)
    }

    fun onSuggestionSelected(product: Product) {
        matchedProductId = product.id
        _state.value = _state.value.copy(
            name = product.name,
            suggestions = emptyList(),
            showSuggestionMenu = false,
            emptySuggestionMessage = null,
            error = null,
        )
        refreshVariants(product.name)
    }

    fun onUseTypedName() {
        matchedProductId = null
        _state.value = _state.value.copy(
            suggestions = emptyList(),
            showSuggestionMenu = false,
            emptySuggestionMessage = null,
            variants = emptyList(),
            preferredVariantId = null,
            error = null,
        )
    }

    fun onQuantityUnitChange(value: ProductUnit) {
        _state.value = _state.value.copy(quantityUnit = value)
    }

    fun onComparisonModeChange(value: Comparison) {
        _state.value = _state.value.copy(comparisonMode = value)
    }

    fun onPreferredVariantSelected(variantId: Int?) {
        _state.value = _state.value.copy(preferredVariantId = variantId)
    }

    fun dismissSuggestionMenu() {
        _state.value = _state.value.copy(showSuggestionMenu = false)
    }

    fun showSuggestionMenu() {
        if (_state.value.suggestions.isNotEmpty()) {
            _state.value = _state.value.copy(showSuggestionMenu = true)
        }
    }

    fun submit() {
        val name = _state.value.name.trim()
        if (name.isEmpty()) {
            _state.value = _state.value.copy(error = "Item name cannot be empty")
            return
        }

        viewModelScope.launch {
            _state.value = _state.value.copy(isSaving = true, error = null)
            runCatching {
                if (itemId == null) {
                    repository.addItem(
                        name = name,
                        preferredVariantId = _state.value.preferredVariantId,
                        quantityUnit = _state.value.quantityUnit,
                        comparisonMode = _state.value.comparisonMode,
                    )
                    true
                } else {
                    repository.updateItem(
                        id = itemId,
                        name = name,
                        preferredVariantId = _state.value.preferredVariantId,
                        quantityUnit = _state.value.quantityUnit,
                        comparisonMode = _state.value.comparisonMode,
                    )
                }
            }.onSuccess { ok ->
                if (ok) {
                    _state.value = _state.value.copy(isSaving = false, shouldClose = true)
                } else {
                    _state.value = _state.value.copy(
                        isSaving = false,
                        error = "Item not found",
                    )
                }
            }.onFailure { error ->
                _state.value = _state.value.copy(
                    isSaving = false,
                    error = error.message ?: "Failed to save item",
                )
            }
        }
    }

    class Factory(
        private val repository: LocalGroceryListRepository,
        private val productCatalogRepository: ProductCatalogRepository,
        private val variantCatalogRepository: ProductVariantCatalogRepository,
        private val itemId: Int?,
    ) : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            @Suppress("UNCHECKED_CAST")
            return EditGroceryListItemViewModel(
                repository,
                productCatalogRepository,
                variantCatalogRepository,
                itemId,
            ) as T
        }
    }

    private fun refreshSuggestions(value: String) {
        val query = value.trim()
        if (query.length < 3) {
            _state.value = _state.value.copy(
                suggestions = emptyList(),
                showSuggestionMenu = false,
                emptySuggestionMessage = null,
            )
            return
        }

        viewModelScope.launch {
            val suggestions = productCatalogRepository.suggestProducts(query, limit = 10)
            _state.value = _state.value.copy(
                suggestions = suggestions,
                showSuggestionMenu = suggestions.isNotEmpty(),
                emptySuggestionMessage = if (suggestions.isEmpty()) {
                    "No products found, but don't worry, you can still add it to your list, we can create it later."
                } else {
                    null
                },
            )
        }
    }

    private fun refreshVariants(value: String) {
        val query = value.trim()
        if (query.isEmpty()) {
            matchedProductId = null
            _state.value = _state.value.copy(
                variants = emptyList(),
                preferredVariantId = null,
            )
            return
        }

        viewModelScope.launch {
            val product = repository.findProductByName(query)
            matchedProductId = product?.id
            val variants = if (product != null) {
                variantCatalogRepository.getCachedOrFetchVariants(product)
            } else {
                emptyList()
            }
            _state.value = _state.value.copy(
                variants = variants,
                preferredVariantId = _state.value.preferredVariantId?.takeIf { id ->
                    variants.any { it.id == id }
                },
            )
        }
    }
}
