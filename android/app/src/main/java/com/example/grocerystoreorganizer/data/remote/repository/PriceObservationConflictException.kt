package com.example.grocerystoreorganizer.data.remote.repository

class PriceObservationConflictException(
    message: String,
    cause: Throwable? = null,
) : IllegalStateException(message, cause)
