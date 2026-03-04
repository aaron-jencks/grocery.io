package com.example.grocerystoreorganizer.data.remote.repository

import com.example.grocerystoreorganizer.grpc.ListProductsRequest
import com.example.grocerystoreorganizer.grpc.ListProductsResponse
import com.example.grocerystoreorganizer.grpc.ListVariantsForProductRequest
import com.example.grocerystoreorganizer.grpc.ListVariantsForProductResponse
import com.example.grocerystoreorganizer.grpc.PriceObservationRequest
import com.example.grocerystoreorganizer.grpc.PriceObservationResponse
import com.example.grocerystoreorganizer.grpc.UpcRequest
import com.example.grocerystoreorganizer.grpc.UpcResponse
import io.grpc.CallOptions
import io.grpc.ManagedChannel
import io.grpc.MethodDescriptor
import io.grpc.okhttp.OkHttpChannelBuilder
import io.grpc.protobuf.lite.ProtoLiteUtils
import io.grpc.stub.ClientCalls

open class GroceryGrpcClient(
    host: String,
    port: Int,
) {
    private val channel: ManagedChannel = OkHttpChannelBuilder.forAddress(host, port)
        .usePlaintext()
        .build()

    open fun resolveUpc(request: UpcRequest): UpcResponse =
        ClientCalls.blockingUnaryCall(channel, RESOLVE_UPC_METHOD, CallOptions.DEFAULT, request)

    open fun listProducts(updatedAfter: String? = null): ListProductsResponse =
        ClientCalls.blockingUnaryCall(
            channel,
            LIST_PRODUCTS_METHOD,
            CallOptions.DEFAULT,
            ListProductsRequest.newBuilder()
                .apply {
                    if (updatedAfter != null) {
                        setUpdatedAfter(updatedAfter)
                    }
                }
                .build(),
        )

    open fun listVariantsForProduct(
        productName: String,
        updatedAfter: String? = null,
    ): ListVariantsForProductResponse =
        ClientCalls.blockingUnaryCall(
            channel,
            LIST_VARIANTS_FOR_PRODUCT_METHOD,
            CallOptions.DEFAULT,
            ListVariantsForProductRequest.newBuilder()
                .setProductName(productName)
                .apply {
                    if (updatedAfter != null) {
                        setUpdatedAfter(updatedAfter)
                    }
                }
                .build(),
        )

    open fun createPriceObservation(request: PriceObservationRequest): PriceObservationResponse =
        ClientCalls.blockingUnaryCall(channel, CREATE_PRICE_OBSERVATION_METHOD, CallOptions.DEFAULT, request)

    open fun shutdown() {
        channel.shutdown()
    }

    companion object {
        private val RESOLVE_UPC_METHOD: MethodDescriptor<UpcRequest, UpcResponse> =
            MethodDescriptor.newBuilder<UpcRequest, UpcResponse>()
                .setType(MethodDescriptor.MethodType.UNARY)
                .setFullMethodName(MethodDescriptor.generateFullMethodName(
                    "grocery.database.UpcService",
                    "ResolveUpc",
                ))
                .setRequestMarshaller(ProtoLiteUtils.marshaller(UpcRequest.getDefaultInstance()))
                .setResponseMarshaller(ProtoLiteUtils.marshaller(UpcResponse.getDefaultInstance()))
                .build()

        private val LIST_PRODUCTS_METHOD: MethodDescriptor<ListProductsRequest, ListProductsResponse> =
            MethodDescriptor.newBuilder<ListProductsRequest, ListProductsResponse>()
                .setType(MethodDescriptor.MethodType.UNARY)
                .setFullMethodName(MethodDescriptor.generateFullMethodName(
                    "grocery.database.CatalogService",
                    "ListProducts",
                ))
                .setRequestMarshaller(
                    ProtoLiteUtils.marshaller(ListProductsRequest.getDefaultInstance())
                )
                .setResponseMarshaller(
                    ProtoLiteUtils.marshaller(ListProductsResponse.getDefaultInstance())
                )
                .build()

        private val LIST_VARIANTS_FOR_PRODUCT_METHOD:
            MethodDescriptor<ListVariantsForProductRequest, ListVariantsForProductResponse> =
            MethodDescriptor.newBuilder<ListVariantsForProductRequest, ListVariantsForProductResponse>()
                .setType(MethodDescriptor.MethodType.UNARY)
                .setFullMethodName(MethodDescriptor.generateFullMethodName(
                    "grocery.database.CatalogService",
                    "ListVariantsForProduct",
                ))
                .setRequestMarshaller(
                    ProtoLiteUtils.marshaller(ListVariantsForProductRequest.getDefaultInstance())
                )
                .setResponseMarshaller(
                    ProtoLiteUtils.marshaller(ListVariantsForProductResponse.getDefaultInstance())
                )
                .build()

        private val CREATE_PRICE_OBSERVATION_METHOD:
            MethodDescriptor<PriceObservationRequest, PriceObservationResponse> =
            MethodDescriptor.newBuilder<PriceObservationRequest, PriceObservationResponse>()
                .setType(MethodDescriptor.MethodType.UNARY)
                .setFullMethodName(MethodDescriptor.generateFullMethodName(
                    "grocery.database.ObservationService",
                    "CreatePriceObservation",
                ))
                .setRequestMarshaller(
                    ProtoLiteUtils.marshaller(PriceObservationRequest.getDefaultInstance())
                )
                .setResponseMarshaller(
                    ProtoLiteUtils.marshaller(PriceObservationResponse.getDefaultInstance())
                )
                .build()
    }
}
