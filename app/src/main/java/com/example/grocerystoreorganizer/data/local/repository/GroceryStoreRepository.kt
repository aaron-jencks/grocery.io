package com.example.grocerystoreorganizer.data.local.repository

import com.example.grocerystoreorganizer.data.local.dao.GroceryItemDao
import com.example.grocerystoreorganizer.data.local.dao.GroceryStoreDao
import com.example.grocerystoreorganizer.data.local.dao.GroceryStoreItemDao
import com.example.grocerystoreorganizer.data.local.entity.GroceryItemEntity
import com.example.grocerystoreorganizer.data.local.entity.GroceryItemQuantifier
import com.example.grocerystoreorganizer.data.local.entity.GroceryStoreEntity
import com.example.grocerystoreorganizer.data.local.entity.GroceryStoreItemEntity

class GroceryStoreRepository(
    private val itemDao: GroceryItemDao,
    private val storeDao: GroceryStoreDao,
    private val storeItemDao: GroceryStoreItemDao
) {
    suspend fun getOrInsertStore(address: String, latitude: Double, longitude: Double): GroceryStoreEntity {
        val clean = address.trim()
        require(clean.isNotEmpty())
        val stores = storeDao.getStoreByAddress(address)
        val storeEntity: GroceryStoreEntity
        if(stores.isEmpty()) {
            storeEntity = GroceryStoreEntity(address, latitude, longitude)
            storeDao.insertStores(storeEntity)
        } else {
            storeEntity = stores[0]
        }
        return storeEntity
    }

    suspend fun getOrInsertItem(itemName: String, itemUPC: Int): GroceryItemEntity {
        val items = itemDao.getItemByUPC(itemUPC)
        val item: GroceryItemEntity
        if(items.isEmpty()) {
            item = GroceryItemEntity(itemUPC, itemName)
            itemDao.insertItems(item)
        } else {
            item = items[0]
        }
        return item
    }

    suspend fun getOrInsertStoreItem(
        store: String, upc: Int,
        price: Double, quantifier: GroceryItemQuantifier
    ): GroceryStoreItemEntity {
        val storeItems = storeItemDao.getItemInformation(store, upc)
        val storeItem: GroceryStoreItemEntity
        if(storeItems.isEmpty()) {
            storeItem = GroceryStoreItemEntity(
                store, upc,
                price, quantifier
            )
            storeItemDao.insertItems(storeItem)
        } else {
            storeItem = storeItems[0]
        }
        return storeItem
    }

    suspend fun updateOrCreateItem(
        address: String, latitude: Double, longitude: Double,
        itemName: String, itemUPC: Int,
        itemPrice: Double, itemQuantifier: GroceryItemQuantifier
    ): GroceryStoreItemEntity {
        getOrInsertStore(address, latitude, longitude)
        getOrInsertItem(itemName, itemUPC)
        val storeItem = getOrInsertStoreItem(address, itemUPC, itemPrice, itemQuantifier)
        if(storeItem.itemPrice != itemPrice || storeItem.itemQuantifier != itemQuantifier) {
            val newStoreItem = GroceryStoreItemEntity(
                address, itemUPC,
                itemPrice, itemQuantifier
            )
            storeItemDao.updateItems(newStoreItem)
            return newStoreItem
        }
        return storeItem
    }

    suspend fun itemExists(upc: Int): Boolean {
        val items = itemDao.getItemByUPC(upc)
        return items.isNotEmpty()
    }

    suspend fun findCheapestStore(
        upc: Int
    ): GroceryStoreItemEntity? {
        val allItems = storeItemDao.getAllItemStores(upc)
        var cheapestStoreItem: GroceryStoreItemEntity? = null
        allItems.forEach {
            if(cheapestStoreItem == null || it.itemPrice < cheapestStoreItem.itemPrice)
                cheapestStoreItem = it
        }
        return cheapestStoreItem
    }
}