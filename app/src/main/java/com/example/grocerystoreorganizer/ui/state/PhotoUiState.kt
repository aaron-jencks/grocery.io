package com.example.grocerystoreorganizer.ui.state

sealed interface PhotoUiState {
    data object Idle : PhotoUiState
    data object NeedsPermission : PhotoUiState
    data object Preparing : PhotoUiState
    data class LaunchCapture(val outputUri: String) : PhotoUiState
    data object Capturing : PhotoUiState
    data class Ready(val outputUri: String) : PhotoUiState
    data class Error(val message: String) : PhotoUiState
}
