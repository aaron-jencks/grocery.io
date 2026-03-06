package com.example.grocerystoreorganizer.ui.grocerylist

import android.content.Intent
import androidx.compose.foundation.gestures.detectDragGesturesAfterLongPress
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.DragHandle
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
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
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.grocerystoreorganizer.EditGroceryListItemActivity
import com.example.grocerystoreorganizer.PriceObservationActivity
import com.example.grocerystoreorganizer.data.local.repository.LocalGroceryListItem
import java.time.OffsetDateTime
import java.time.format.DateTimeParseException
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
    val mode by vm.mode.collectAsStateWithLifecycle()
    val optimizationLoading by vm.optimizationLoading.collectAsStateWithLifecycle()
    val optimizationResult by vm.optimizationResult.collectAsStateWithLifecycle()
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
                    if (mode == GroceryListMode.EDIT) {
                        Button(onClick = vm::optimizeShoppingPlan) {
                            Text("Optimize")
                        }
                    } else {
                        Button(onClick = vm::backToEditMode) {
                            Text("Edit")
                        }
                    }
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
            if (mode == GroceryListMode.EDIT) {
                FloatingActionButton(
                    onClick = {
                        context.startActivity(EditGroceryListItemActivity.createIntent(context))
                    }
                ) {
                    Icon(Icons.Default.Add, contentDescription = "Add grocery list item")
                }
            }
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { padding ->
        when (mode) {
            GroceryListMode.EDIT -> EditModeContent(
                items = items,
                paddingModifier = Modifier.padding(padding),
                onEdit = { id ->
                    context.startActivity(EditGroceryListItemActivity.createIntent(context, id))
                },
                onDelete = vm::deleteItem,
                onIncrement = vm::incrementDesiredCount,
                onDecrement = vm::decrementDesiredCount,
                onMove = vm::moveItem,
                draggingItemId = draggingItemId,
                onDragStart = { draggingItemId = it },
                onDragDelta = { dragAccumulatedY += it },
                onDragEnd = {
                    draggingItemId = -1
                    dragAccumulatedY = 0f
                },
                dragAccumulatedY = dragAccumulatedY,
                setDragAccumulatedY = { dragAccumulatedY = it },
            )

            GroceryListMode.OPTIMIZED -> OptimizedModeContent(
                loading = optimizationLoading,
                result = optimizationResult,
                onToggleChecked = vm::toggleOptimizedItemChecked,
                onCompleteList = vm::completeList,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(horizontal = 12.dp, vertical = 8.dp),
            )
        }
    }
}

@Composable
private fun EditModeContent(
    items: List<LocalGroceryListItem>,
    paddingModifier: Modifier,
    onEdit: (Int) -> Unit,
    onDelete: (Int) -> Unit,
    onIncrement: (Int) -> Unit,
    onDecrement: (Int) -> Unit,
    onMove: (Int, Int) -> Unit,
    draggingItemId: Int,
    onDragStart: (Int) -> Unit,
    onDragDelta: (Float) -> Unit,
    onDragEnd: () -> Unit,
    dragAccumulatedY: Float,
    setDragAccumulatedY: (Float) -> Unit,
) {
    if (items.isEmpty()) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .then(paddingModifier),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                "No items yet. Tap + to add one.",
                style = MaterialTheme.typography.bodyLarge,
            )
        }
        return
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .then(paddingModifier),
        verticalArrangement = Arrangement.spacedBy(1.dp),
    ) {
        itemsIndexed(items, key = { _, item -> item.id }) { index, item ->
            GroceryListRow(
                item = item,
                onClick = { onEdit(item.id) },
                onDelete = { onDelete(item.id) },
                onIncrement = { onIncrement(item.id) },
                onDecrement = { onDecrement(item.id) },
                onDragDelta = { deltaY ->
                    onDragStart(item.id)
                    val nextAccumulated = dragAccumulatedY + deltaY
                    onDragDelta(deltaY)
                    if (abs(nextAccumulated) >= 72f) {
                        val direction = if (nextAccumulated > 0) 1 else -1
                        val targetIndex = (index + direction).coerceIn(0, items.lastIndex)
                        if (targetIndex != index) {
                            onMove(index, targetIndex)
                        }
                        setDragAccumulatedY(0f)
                    }
                },
                onDragEnd = onDragEnd,
                isDragging = draggingItemId == item.id,
            )
        }
    }
}

@Composable
private fun OptimizedModeContent(
    loading: Boolean,
    result: OptimizationResultUi,
    onToggleChecked: (Int) -> Unit,
    onCompleteList: () -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        if (loading) {
            item {
                Text("Optimizing...", style = MaterialTheme.typography.bodyLarge)
            }
        }
        items(result.warnings) { warning ->
            Text(
                text = "Warning: $warning",
                color = MaterialTheme.colorScheme.tertiary,
                style = MaterialTheme.typography.bodySmall,
            )
        }
        items(result.groups) { group ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier.padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text(group.storeName, style = MaterialTheme.typography.titleMedium)
                    group.items.forEach { item ->
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            Checkbox(
                                checked = item.checked,
                                onCheckedChange = { onToggleChecked(item.itemId) },
                            )
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = "${item.itemName} (${item.variantLabel})",
                                    textDecoration = if (item.checked) TextDecoration.LineThrough else null,
                                )
                                Text(
                                    text = "Observed: ${formatObservedAt(item.observedAt)}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            Text(
                                text = "$${"%.2f".format(item.estimatedPrice)}",
                                textDecoration = if (item.checked) TextDecoration.LineThrough else null,
                            )
                        }
                    }
                    Text(
                        text = "Store Total: $${"%.2f".format(group.totalPrice)}",
                        style = MaterialTheme.typography.titleSmall,
                    )
                }
            }
        }
        if (result.unknown.isNotEmpty()) {
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        Text("Unknown", style = MaterialTheme.typography.titleMedium)
                        result.unknown.forEach { unknown ->
                            Text("• $unknown", style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }
        }
        item {
            Text(
                text = "Total: $${"%.2f".format(result.totalPrice)}",
                style = MaterialTheme.typography.titleMedium,
            )
        }
        item {
            Button(
                modifier = Modifier.fillMaxWidth(),
                onClick = onCompleteList,
            ) {
                Text("Complete List")
            }
        }
    }
}

private fun formatObservedAt(raw: String): String =
    try {
        val timestamp = OffsetDateTime.parse(raw)
        timestamp.toLocalDate().toString()
    } catch (_: DateTimeParseException) {
        raw
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
