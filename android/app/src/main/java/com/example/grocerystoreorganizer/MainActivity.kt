package com.example.grocerystoreorganizer

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.lifecycle.lifecycleScope
import androidx.compose.material3.MaterialTheme
import com.example.grocerystoreorganizer.data.local.repository.ProductCatalogRepository
import com.example.grocerystoreorganizer.data.local.db.DatabaseProvider
import com.example.grocerystoreorganizer.data.local.repository.LocalGroceryListRepository
import com.example.grocerystoreorganizer.data.remote.repository.GroceryGrpcClient
import com.example.grocerystoreorganizer.data.remote.repository.GrpcShoppingOptimizationRepository
import com.example.grocerystoreorganizer.data.remote.repository.ProductCatalogSyncer
import com.example.grocerystoreorganizer.ui.grocerylist.GroceryListScreen
import com.example.grocerystoreorganizer.ui.grocerylist.GroceryListViewModel
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
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
                }.onSuccess {
                    Toast.makeText(
                        this@MainActivity,
                        "Connected to server",
                        Toast.LENGTH_SHORT,
                    ).show()
                }
            }
        }
        setContent {
            MaterialTheme {
                GroceryListScreen(
                    factory = GroceryListViewModel.Factory(
                        repository = repository,
                        optimizationRepository = grpcClient?.let { GrpcShoppingOptimizationRepository(it) },
                    )
                )
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        grpcClient?.shutdown()
    }
}
