package com.example.grocerystoreorganizer.data.local.repository

sealed interface CameraResult {
    data class Ready(val outputUri: String) : CameraResult
    data object NoPermission : CameraResult
    data class Error(val message: String) : CameraResult
}
