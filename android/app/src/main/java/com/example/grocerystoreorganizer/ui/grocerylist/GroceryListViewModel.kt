package com.example.grocerystoreorganizer.ui.grocerylist

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.grocerystoreorganizer.data.local.repository.LocalGroceryListItem
import com.example.grocerystoreorganizer.data.local.repository.LocalGroceryListRepository
import com.example.grocerystoreorganizer.data.remote.repository.GrpcShoppingOptimizationRepository
import com.example.grocerystoreorganizer.data.remote.repository.ShoppingOptimizationItemRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

enum class GroceryListMode {
    EDIT,
    OPTIMIZED,
}

data class OptimizedItemUi(
    val itemId: Int,
    val itemName: String,
    val variantLabel: String,
    val observedAt: String,
    val estimatedPrice: Double,
    val checked: Boolean,
)

data class OptimizedStoreGroupUi(
    val storeName: String,
    val totalPrice: Double,
    val items: List<OptimizedItemUi>,
)

data class OptimizationResultUi(
    val groups: List<OptimizedStoreGroupUi> = emptyList(),
    val unknown: List<String> = emptyList(),
    val warnings: List<String> = emptyList(),
    val totalPrice: Double = 0.0,
)

class GroceryListViewModel(
    private val repository: LocalGroceryListRepository,
    private val optimizationRepository: GrpcShoppingOptimizationRepository?,
) : ViewModel() {
    val items: StateFlow<List<LocalGroceryListItem>> = repository.observeItems()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()
    private val _mode = MutableStateFlow(GroceryListMode.EDIT)
    val mode: StateFlow<GroceryListMode> = _mode.asStateFlow()
    private val _optimizationLoading = MutableStateFlow(false)
    val optimizationLoading: StateFlow<Boolean> = _optimizationLoading.asStateFlow()
    private val _optimizationResult = MutableStateFlow(OptimizationResultUi())
    val optimizationResult: StateFlow<OptimizationResultUi> = _optimizationResult.asStateFlow()
    private val _checkedOptimizedIds = MutableStateFlow(setOf<Int>())
    val checkedOptimizedIds: StateFlow<Set<Int>> = _checkedOptimizedIds.asStateFlow()

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

    fun optimizeShoppingPlan() {
        val localItems = items.value
        if (localItems.isEmpty()) {
            _error.value = "Add grocery items before optimization"
            return
        }
        val remote = optimizationRepository
        if (remote == null) {
            _error.value = "Server optimization is unavailable"
            return
        }

        viewModelScope.launch {
            _optimizationLoading.value = true
            runCatching {
                remote.optimize(
                    localItems.map { item ->
                        ShoppingOptimizationItemRequest(
                            itemId = item.id,
                            productName = item.productName,
                            desiredCount = item.desiredCount,
                            comparisonMode = item.comparisonMode,
                            preferredUpc = item.preferredVariantUpc,
                        )
                    }
                )
            }.onSuccess { response ->
                val nameById = localItems.associateBy({ it.id }, { it.productName })
                val checkedIds = _checkedOptimizedIds.value
                val groups = response.matches
                    .groupBy { it.storeId to "${it.storeName ?: "Unknown Store"} (${it.storeAddress})" }
                    .values
                    .map { group ->
                        val storeName = "${group.first().storeName ?: "Unknown Store"} (${group.first().storeAddress})"
                        val uiItems = group
                            .sortedBy { it.variantProductName }
                            .map { match ->
                                OptimizedItemUi(
                                    itemId = match.itemId,
                                    itemName = nameById[match.itemId] ?: match.variantProductName,
                                    variantLabel = match.variantLabel,
                                    observedAt = match.observedAt,
                                    estimatedPrice = match.estimatedTotalPrice,
                                    checked = checkedIds.contains(match.itemId),
                                )
                            }
                        OptimizedStoreGroupUi(
                            storeName = storeName,
                            totalPrice = uiItems.sumOf { it.estimatedPrice },
                            items = uiItems,
                        )
                    }
                    .sortedWith(compareBy<OptimizedStoreGroupUi> { it.totalPrice }.thenBy { it.storeName })
                _optimizationResult.value = OptimizationResultUi(
                    groups = groups,
                    unknown = response.unmatched
                        .filter { !it.reason.startsWith("Warning:", ignoreCase = true) }
                        .map { unmatched ->
                            "${nameById[unmatched.itemId] ?: unmatched.productName}: ${unmatched.reason}"
                        },
                    warnings = response.unmatched
                        .filter { it.reason.startsWith("Warning:", ignoreCase = true) }
                        .map { warning ->
                            "${nameById[warning.itemId] ?: warning.productName}: Approximate unit comparison was used; result may be suboptimal."
                        },
                    totalPrice = groups.sumOf { it.totalPrice },
                )
                _mode.value = GroceryListMode.OPTIMIZED
            }.onFailure { throwable ->
                _error.value = throwable.message ?: "Failed to optimize grocery list"
            }
            _optimizationLoading.value = false
        }
    }

    fun backToEditMode() {
        _mode.value = GroceryListMode.EDIT
    }

    fun toggleOptimizedItemChecked(itemId: Int) {
        val next = _checkedOptimizedIds.value.toMutableSet()
        if (!next.add(itemId)) {
            next.remove(itemId)
        }
        _checkedOptimizedIds.value = next
        // Rebuild check states in-place for current optimization result.
        val updatedGroups = _optimizationResult.value.groups.map { group ->
            group.copy(
                items = group.items.map { item ->
                    item.copy(checked = next.contains(item.itemId))
                }
            )
        }
        _optimizationResult.value = _optimizationResult.value.copy(groups = updatedGroups)
    }

    fun completeList() {
        viewModelScope.launch {
            repository.clearAllItems()
            _checkedOptimizedIds.value = emptySet()
            _optimizationResult.value = OptimizationResultUi()
            _mode.value = GroceryListMode.EDIT
        }
    }

    class Factory(
        private val repository: LocalGroceryListRepository,
        private val optimizationRepository: GrpcShoppingOptimizationRepository?,
    ) : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            @Suppress("UNCHECKED_CAST")
            return GroceryListViewModel(repository, optimizationRepository) as T
        }
    }
}
