package com.example.grocerystoreorganizer

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.lifecycle.lifecycleScope
import androidx.compose.material3.MaterialTheme
import com.example.grocerystoreorganizer.data.local.db.DatabaseProvider
import com.example.grocerystoreorganizer.data.local.repository.LocalGroceryListRepository
import com.example.grocerystoreorganizer.data.local.repository.ProductCatalogRepository
import com.example.grocerystoreorganizer.data.remote.repository.GroceryGrpcClient
import com.example.grocerystoreorganizer.data.remote.repository.ProductCatalogSyncer
import com.example.grocerystoreorganizer.data.remote.repository.ProductVariantCatalogRepository
import com.example.grocerystoreorganizer.ui.grocerylist.EditGroceryListItemScreen
import com.example.grocerystoreorganizer.ui.grocerylist.EditGroceryListItemViewModel
import kotlinx.coroutines.launch

class EditGroceryListItemActivity : ComponentActivity() {
    private var grpcClient: GroceryGrpcClient? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val db = DatabaseProvider.get(this)
        val repository = LocalGroceryListRepository(
            dao = db.localGroceryListEntryDao(),
            productDao = db.productDao(),
            variantDao = db.productVariantDao(),
        )
        val productCatalogRepository = ProductCatalogRepository(db.productDao())
        grpcClient = if (BuildConfig.USE_REMOTE_DB) {
            GroceryGrpcClient(BuildConfig.GRPC_HOST, BuildConfig.GRPC_PORT)
        } else {
            null
        }
        grpcClient?.let { client ->
            lifecycleScope.launch {
                runCatching {
                    ProductCatalogSyncer(client, productCatalogRepository).syncFromServer()
                }
            }
        }
        val variantCatalogRepository = ProductVariantCatalogRepository(
            variantDao = db.productVariantDao(),
            client = grpcClient,
        )
        val itemId = intent.getIntExtra(EXTRA_ITEM_ID, NO_ITEM_ID)
            .takeIf { it != NO_ITEM_ID }

        setContent {
            MaterialTheme {
                EditGroceryListItemScreen(
                    title = if (itemId == null) "Add Grocery Item" else "Edit Grocery Item",
                    factory = EditGroceryListItemViewModel.Factory(
                        repository = repository,
                        productCatalogRepository = productCatalogRepository,
                        variantCatalogRepository = variantCatalogRepository,
                        itemId = itemId,
                    ),
                    onClose = ::finish,
                )
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        grpcClient?.shutdown()
    }

    companion object {
        private const val EXTRA_ITEM_ID = "item_id"
        private const val NO_ITEM_ID = -1

        fun createIntent(context: Context, itemId: Int? = null): Intent =
            Intent(context, EditGroceryListItemActivity::class.java).apply {
                if (itemId != null) {
                    putExtra(EXTRA_ITEM_ID, itemId)
                }
            }
    }
}
