package com.example.grocerystoreorganizer.ui.state

sealed interface PhotoUiState {
    data object Idle : PhotoUiState
    data object Capturing : PhotoUiState
    data object Processing : PhotoUiState
    data class Ready(val previewDescription: String) : PhotoUiState
    data class Error(val message: String) : PhotoUiState
}