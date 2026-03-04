package com.example.grocerystoreorganizer.data.local.source

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import java.io.File
import java.io.IOException

class CameraDataSource(
    private val context: Context
) {
    fun hasCameraPermission(): Boolean =
        ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED

    fun createImageUri(): Uri? {
        val imageFile = createImageFile() ?: return null
        return runCatching {
            FileProvider.getUriForFile(
                context,
                "${context.packageName}.fileprovider",
                imageFile
            )
        }.getOrNull()
    }

    private fun createImageFile(): File? {
        val dir = File(context.cacheDir, "captured_images").apply {
            if (!exists()) mkdirs()
        }
        if (!dir.exists()) return null
        return try {
            File.createTempFile("price_", ".jpg", dir)
        } catch (_: IOException) {
            null
        }
    }
}
