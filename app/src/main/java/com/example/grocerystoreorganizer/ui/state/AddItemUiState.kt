package com.example.grocerystoreorganizer.ui.state

import com.example.grocerystoreorganizer.data.local.entity.GroceryItemQuantifier

data class AddItemUiState(
    val storeAddress: String = "",
    val storeLatitude: String = "",
    val storeLongitude: String = "",
    val itemName: String = "",
    val itemUPC: String = "",
    val itemPrice: String = "",
    val itemQuantifier: GroceryItemQuantifier = GroceryItemQuantifier.OUNCE,

    val location: LocationUiState = LocationUiState.Idle,
    val photo: PhotoUiState = PhotoUiState.Idle,

    val isSaving: Boolean = false,
    val savedId: Long? = null,

    val nameError: String? = null,
    val upcError: String? = null,
    val priceError: String? = null,
    val generalError: String? = null
)
