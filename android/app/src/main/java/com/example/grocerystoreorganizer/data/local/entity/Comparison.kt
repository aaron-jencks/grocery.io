package com.example.grocerystoreorganizer.data.local.entity

enum class Comparison(val display: String, val description: String) {
    cheapestPrice("Cheapest Price", "Cheapest price for desired quantity"),
    bestUnitValue("Best Unit Value", "Best per unit price, regardless of quantity"),
}