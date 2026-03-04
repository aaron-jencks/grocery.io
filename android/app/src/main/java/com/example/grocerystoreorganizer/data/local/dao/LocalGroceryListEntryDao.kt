package com.example.grocerystoreorganizer.data.local.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.grocerystoreorganizer.data.local.entity.LocalGroceryListEntry
import com.example.grocerystoreorganizer.data.local.repository.LocalGroceryListItem
import kotlinx.coroutines.flow.Flow

@Dao
interface LocalGroceryListEntryDao {
    @Query(
        """
        select
            e.rowid as id,
            e.productId as productId,
            p.name as productName,
            e.preferredVariantId as preferredVariantId,
            v.label as preferredVariantLabel,
            v.packCount as preferredVariantPackCount,
            v.netQuantity as preferredVariantNetQuantity,
            v.quantityUnit as preferredVariantQuantityUnit,
            e.quantityUnit as quantityUnit,
            e.comparisonMode as comparisonMode,
            e.desiredCount as desiredCount,
            e.sortOrder as sortOrder
        from local_grocery_list_entries e
        join products p on p.rowid = e.productId
        left join variants v on v.rowid = e.preferredVariantId
        order by e.sortOrder asc, e.rowid asc
        """
    )
    fun observeAll(): Flow<List<LocalGroceryListItem>>

    @Query("select * from local_grocery_list_entries where rowid = :id")
    suspend fun findById(id: Int): LocalGroceryListEntry?

    @Query("select coalesce(max(sortOrder), -1) from local_grocery_list_entries")
    suspend fun findMaxSortOrder(): Int

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insert(item: LocalGroceryListEntry): Long

    @Update
    suspend fun updateItems(vararg items: LocalGroceryListEntry): Int

    @Delete
    suspend fun delete(item: LocalGroceryListEntry): Int
}
