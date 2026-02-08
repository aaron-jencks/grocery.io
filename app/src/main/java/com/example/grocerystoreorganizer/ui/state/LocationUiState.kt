package com.example.grocerystoreorganizer.ui.state


sealed interface LocationUiState {
    object Idle : LocationUiState
    object NeedsPermission : LocationUiState
    object Loading : LocationUiState
    data class Ready(val address: String, val latitude: Double, val longitude: Double) : LocationUiState
    data class Error(val message: String) : LocationUiState
}