package com.example.grocerystoreorganizer.data.local.repository

import com.example.grocerystoreorganizer.data.local.source.CameraDataSource

class CameraRepository(
    private val dataSource: CameraDataSource
) {
    fun hasCameraPermission(): Boolean = dataSource.hasCameraPermission()

    fun prepareCapture(): CameraResult {
        if (!hasCameraPermission()) return CameraResult.NoPermission
        val uri = dataSource.createImageUri() ?: return CameraResult.Error("Could not prepare image capture")
        return CameraResult.Ready(uri.toString())
    }
}
