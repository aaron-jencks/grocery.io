package com.example.grocerystoreorganizer.ui.grocerylist

import android.content.Intent
import androidx.compose.foundation.gestures.detectDragGesturesAfterLongPress
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.DragHandle
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.Button
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.safeDrawing
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.grocerystoreorganizer.EditGroceryListItemActivity
import com.example.grocerystoreorganizer.PriceObservationActivity
import com.example.grocerystoreorganizer.data.local.repository.LocalGroceryListItem
import kotlin.math.abs

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GroceryListScreen(
    factory: GroceryListViewModel.Factory,
) {
    val context = LocalContext.current
    val vm: GroceryListViewModel = viewModel(factory = factory)
    val items by vm.items.collectAsStateWithLifecycle()
    val error by vm.error.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }
    var draggingItemId by remember { mutableIntStateOf(-1) }
    var dragAccumulatedY by remember { mutableFloatStateOf(0f) }

    LaunchedEffect(error) {
        if (error != null) {
            snackbarHostState.showSnackbar(error!!)
            vm.clearError()
        }
    }

    Scaffold(
        contentWindowInsets = WindowInsets.safeDrawing,
        topBar = {
            TopAppBar(
                modifier = Modifier.statusBarsPadding(),
                title = { Text("Grocery List") },
                actions = {
                    Button(
                        onClick = {
                            context.startActivity(
                                Intent(context, PriceObservationActivity::class.java)
                            )
                        }
                    ) {
                        Text(
                            text = "$",
                            color = MaterialTheme.colorScheme.onPrimary,
                            style = MaterialTheme.typography.titleLarge,
                        )
                    }
                }
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = {
                    context.startActivity(EditGroceryListItemActivity.createIntent(context))
                }
            ) {
                Icon(Icons.Default.Add, contentDescription = "Add grocery list item")
            }
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { padding ->
        if (items.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    "No items yet. Tap + to add one.",
                    style = MaterialTheme.typography.bodyLarge,
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                verticalArrangement = Arrangement.spacedBy(1.dp),
            ) {
                itemsIndexed(items, key = { _, item -> item.id }) { index, item ->
                    GroceryListRow(
                        item = item,
                        onClick = {
                            context.startActivity(
                                EditGroceryListItemActivity.createIntent(context, item.id)
                            )
                        },
                        onDelete = { vm.deleteItem(item.id) },
                        onIncrement = { vm.incrementDesiredCount(item.id) },
                        onDecrement = { vm.decrementDesiredCount(item.id) },
                        onDragDelta = { deltaY ->
                            draggingItemId = item.id
                            dragAccumulatedY += deltaY
                            if (abs(dragAccumulatedY) >= 72f) {
                                val direction = if (dragAccumulatedY > 0) 1 else -1
                                val targetIndex = (index + direction).coerceIn(0, items.lastIndex)
                                if (targetIndex != index) {
                                    vm.moveItem(index, targetIndex)
                                }
                                dragAccumulatedY = 0f
                            }
                        },
                        onDragEnd = {
                            draggingItemId = -1
                            dragAccumulatedY = 0f
                        },
                        isDragging = draggingItemId == item.id,
                    )
                }
            }
        }
    }
}

@Composable
private fun GroceryListRow(
    item: LocalGroceryListItem,
    onClick: () -> Unit,
    onDelete: () -> Unit,
    onIncrement: () -> Unit,
    onDecrement: () -> Unit,
    onDragDelta: (Float) -> Unit,
    onDragEnd: () -> Unit,
    isDragging: Boolean,
) {
    Surface(
        tonalElevation = if (isDragging) 4.dp else 0.dp,
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Icon(
                imageVector = Icons.Default.DragHandle,
                contentDescription = "Reorder item",
                modifier = Modifier.pointerInput(item.id) {
                    detectDragGesturesAfterLongPress(
                        onDrag = { change, dragAmount ->
                            change.consume()
                            onDragDelta(dragAmount.y)
                        },
                        onDragEnd = onDragEnd,
                        onDragCancel = onDragEnd,
                    )
                }
            )
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(2.dp),
            ) {
                Text(
                    text = item.productName,
                    style = MaterialTheme.typography.bodyLarge,
                )
                item.preferredVariantLabel?.let { label ->
                    val quantity = item.preferredVariantNetQuantity
                    val unit = item.preferredVariantQuantityUnit?.display
                    val pack = item.preferredVariantPackCount
                    Text(
                        text = buildString {
                            append(label)
                            if (pack != null && quantity != null && unit != null) {
                                append(" • ")
                                append(pack)
                                append(" x ")
                                append(quantity)
                                append(" ")
                                append(unit)
                            }
                        },
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(2.dp),
            ) {
                IconButton(onClick = onDecrement) {
                    Icon(Icons.Default.Remove, contentDescription = "Decrease desired count")
                }
                Text(
                    text = item.desiredCount.toString(),
                    style = MaterialTheme.typography.titleMedium,
                )
                IconButton(onClick = onIncrement) {
                    Icon(Icons.Default.Add, contentDescription = "Increase desired count")
                }
            }
            IconButton(onClick = onDelete) {
                Icon(Icons.Default.Delete, contentDescription = "Delete item")
            }
        }
    }
}
