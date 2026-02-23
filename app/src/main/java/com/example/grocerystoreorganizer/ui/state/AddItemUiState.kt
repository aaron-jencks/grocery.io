package com.example.grocerystoreorganizer.ui.state

import com.example.grocerystoreorganizer.data.local.entity.ProductUnit

data class AddItemUiState(
    val storeName: String = "",
    val storeAddress: String = "",
    val storeLatitude: String = "",
    val storeLongitude: String = "",
    val productName: String = "",
    val productCategory: String = "",
    val variantLabel: String = "",
    val itemUPC: String = "",
    val upcResolved: Boolean = false,
    val requiresProductVariantDetails: Boolean = false,
    val isResolvingUpc: Boolean = false,
    val upcLookupMessage: String? = null,
    val packCount: String = "1",
    val netQuantity: String = "",
    val quantityUnit: ProductUnit = ProductUnit.EA,
    val isVariableWeight: Boolean = false,
    val itemPrice: String = "",
    val observedAt: String = "",
    val isSale: Boolean = false,
    val saleStartDate: String = "",
    val saleExpirationDate: String = "",
    val saleMinimumQuantity: String = "",
    val saleLimitQuantity: String = "",

    val location: LocationUiState = LocationUiState.Idle,
    val photo: PhotoUiState = PhotoUiState.Idle,

    val isSaving: Boolean = false,
    val savedId: Int? = null,

    val productError: String? = null,
    val storeAddressError: String? = null,
    val latitudeError: String? = null,
    val longitudeError: String? = null,
    val variantError: String? = null,
    val upcError: String? = null,
    val packCountError: String? = null,
    val netQuantityError: String? = null,
    val priceError: String? = null,
    val observedAtError: String? = null,
    val saleStartDateError: String? = null,
    val generalError: String? = null
)
