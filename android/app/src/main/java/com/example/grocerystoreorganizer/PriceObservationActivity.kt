package com.example.grocerystoreorganizer

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import com.example.grocerystoreorganizer.data.local.entity.PackagingStyle
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.ui.additem.AddItemScreen
import com.example.grocerystoreorganizer.ui.additem.PriceObservationPrefill

class PriceObservationActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefill = readPrefillFromIntent()
        val sourceItemId = intent.getIntExtra(EXTRA_SOURCE_ITEM_ID, NO_SOURCE_ITEM_ID)
        setContent {
            MaterialTheme {
                AddItemScreen(
                    prefill = prefill,
                    onObservationSaved = {
                        if (sourceItemId != NO_SOURCE_ITEM_ID) {
                            setResult(
                                RESULT_OK,
                                Intent().putExtra(EXTRA_COMPLETED_ITEM_ID, sourceItemId),
                            )
                        } else {
                            setResult(RESULT_OK)
                        }
                        finish()
                    },
                )
            }
        }
    }

    private fun readPrefillFromIntent(): PriceObservationPrefill? {
        val productName = sanitizeProductName(intent.getStringExtra(EXTRA_PRODUCT_NAME))
        if (productName.isEmpty()) return null
        val quantityUnit = intent.getStringExtra(EXTRA_QUANTITY_UNIT)?.let { raw ->
            runCatching { ProductUnit.valueOf(raw) }.getOrNull()
        }
        val packagingStyle = intent.getStringExtra(EXTRA_PACKAGING_STYLE)?.let { raw ->
            runCatching { PackagingStyle.valueOf(raw) }.getOrNull()
        }
        return PriceObservationPrefill(
            productName = productName,
            productCategory = intent.getStringExtra(EXTRA_PRODUCT_CATEGORY),
            variantLabel = intent.getStringExtra(EXTRA_VARIANT_LABEL),
            brand = intent.getStringExtra(EXTRA_BRAND),
            flavor = intent.getStringExtra(EXTRA_FLAVOR),
            packagingStyle = packagingStyle,
            upc = intent.getStringExtra(EXTRA_UPC),
            packCount = intent.getIntExtra(EXTRA_PACK_COUNT, Int.MIN_VALUE).takeIf { it != Int.MIN_VALUE },
            netQuantity = intent.getDoubleExtra(EXTRA_NET_QUANTITY, Double.NaN).takeIf { !it.isNaN() },
            quantityUnit = quantityUnit,
            isVariableWeight = intent.getBooleanExtra(EXTRA_IS_VARIABLE_WEIGHT, false),
        )
    }

    companion object {
        private const val EXTRA_PRODUCT_NAME = "price_obs_product_name"
        private const val EXTRA_PRODUCT_CATEGORY = "price_obs_product_category"
        private const val EXTRA_VARIANT_LABEL = "price_obs_variant_label"
        private const val EXTRA_BRAND = "price_obs_brand"
        private const val EXTRA_FLAVOR = "price_obs_flavor"
        private const val EXTRA_PACKAGING_STYLE = "price_obs_packaging_style"
        private const val EXTRA_UPC = "price_obs_upc"
        private const val EXTRA_PACK_COUNT = "price_obs_pack_count"
        private const val EXTRA_NET_QUANTITY = "price_obs_net_quantity"
        private const val EXTRA_QUANTITY_UNIT = "price_obs_quantity_unit"
        private const val EXTRA_IS_VARIABLE_WEIGHT = "price_obs_is_variable_weight"
        private const val EXTRA_SOURCE_ITEM_ID = "price_obs_source_item_id"
        private const val EXTRA_COMPLETED_ITEM_ID = "price_obs_completed_item_id"
        private const val NO_SOURCE_ITEM_ID = -1

        fun createIntent(
            context: Context,
            prefill: PriceObservationPrefill? = null,
            sourceItemId: Int? = null,
        ): Intent =
            Intent(context, PriceObservationActivity::class.java).apply {
                if (prefill != null) {
                    putExtra(EXTRA_PRODUCT_NAME, prefill.productName)
                    prefill.productCategory?.let { putExtra(EXTRA_PRODUCT_CATEGORY, it) }
                    prefill.variantLabel?.let { putExtra(EXTRA_VARIANT_LABEL, it) }
                    prefill.brand?.let { putExtra(EXTRA_BRAND, it) }
                    prefill.flavor?.let { putExtra(EXTRA_FLAVOR, it) }
                    prefill.packagingStyle?.let { putExtra(EXTRA_PACKAGING_STYLE, it.name) }
                    prefill.upc?.let { putExtra(EXTRA_UPC, it) }
                    prefill.packCount?.let { putExtra(EXTRA_PACK_COUNT, it) }
                    prefill.netQuantity?.let { putExtra(EXTRA_NET_QUANTITY, it) }
                    prefill.quantityUnit?.let { putExtra(EXTRA_QUANTITY_UNIT, it.name) }
                    putExtra(EXTRA_IS_VARIABLE_WEIGHT, prefill.isVariableWeight)
                }
                sourceItemId?.let { putExtra(EXTRA_SOURCE_ITEM_ID, it) }
            }

        fun extractCompletedItemId(resultIntent: Intent?): Int? {
            if (resultIntent == null) return null
            val id = resultIntent.getIntExtra(EXTRA_COMPLETED_ITEM_ID, NO_SOURCE_ITEM_ID)
            return id.takeIf { it != NO_SOURCE_ITEM_ID }
        }

        private fun sanitizeProductName(value: String?): String {
            val normalized = value?.trim().orEmpty()
            if (normalized.equals("no product information available", ignoreCase = true)) return ""
            if (normalized.equals("unknown product", ignoreCase = true)) return ""
            return normalized
        }
    }
}
