from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ProductUnit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    OZ: _ClassVar[ProductUnit]
    LB: _ClassVar[ProductUnit]
    EA: _ClassVar[ProductUnit]
    ITEM: _ClassVar[ProductUnit]
    KG: _ClassVar[ProductUnit]
    G: _ClassVar[ProductUnit]
    LIT: _ClassVar[ProductUnit]
    ML: _ClassVar[ProductUnit]
    GAL: _ClassVar[ProductUnit]
    QT: _ClassVar[ProductUnit]
    PT: _ClassVar[ProductUnit]
    TSP: _ClassVar[ProductUnit]
    TBSP: _ClassVar[ProductUnit]
    FL_OZ: _ClassVar[ProductUnit]
    CUP: _ClassVar[ProductUnit]

class ComparisonMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CHEAPEST_PRICE: _ClassVar[ComparisonMode]
    BEST_UNIT_VALUE: _ClassVar[ComparisonMode]

class PackagingStyle(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PACKAGING_UNSPECIFIED: _ClassVar[PackagingStyle]
    LOOSE: _ClassVar[PackagingStyle]
    CAN: _ClassVar[PackagingStyle]
    BOTTLE: _ClassVar[PackagingStyle]
    BOX: _ClassVar[PackagingStyle]
    BAG: _ClassVar[PackagingStyle]
    CARTON: _ClassVar[PackagingStyle]
    BUNCH: _ClassVar[PackagingStyle]
    OTHER: _ClassVar[PackagingStyle]
OZ: ProductUnit
LB: ProductUnit
EA: ProductUnit
ITEM: ProductUnit
KG: ProductUnit
G: ProductUnit
LIT: ProductUnit
ML: ProductUnit
GAL: ProductUnit
QT: ProductUnit
PT: ProductUnit
TSP: ProductUnit
TBSP: ProductUnit
FL_OZ: ProductUnit
CUP: ProductUnit
CHEAPEST_PRICE: ComparisonMode
BEST_UNIT_VALUE: ComparisonMode
PACKAGING_UNSPECIFIED: PackagingStyle
LOOSE: PackagingStyle
CAN: PackagingStyle
BOTTLE: PackagingStyle
BOX: PackagingStyle
BAG: PackagingStyle
CARTON: PackagingStyle
BUNCH: PackagingStyle
OTHER: PackagingStyle

class UpcRequest(_message.Message):
    __slots__ = ("upc",)
    UPC_FIELD_NUMBER: _ClassVar[int]
    upc: str
    def __init__(self, upc: _Optional[str] = ...) -> None: ...

class UpcInfo(_message.Message):
    __slots__ = ("upc", "productName", "productCategory", "variantLabel", "packCount", "netQuantity", "quantityUnit", "isVariableWeight", "updatedAt", "brand", "flavor", "packagingStyle", "noUpcAvailable")
    UPC_FIELD_NUMBER: _ClassVar[int]
    PRODUCTNAME_FIELD_NUMBER: _ClassVar[int]
    PRODUCTCATEGORY_FIELD_NUMBER: _ClassVar[int]
    VARIANTLABEL_FIELD_NUMBER: _ClassVar[int]
    PACKCOUNT_FIELD_NUMBER: _ClassVar[int]
    NETQUANTITY_FIELD_NUMBER: _ClassVar[int]
    QUANTITYUNIT_FIELD_NUMBER: _ClassVar[int]
    ISVARIABLEWEIGHT_FIELD_NUMBER: _ClassVar[int]
    UPDATEDAT_FIELD_NUMBER: _ClassVar[int]
    BRAND_FIELD_NUMBER: _ClassVar[int]
    FLAVOR_FIELD_NUMBER: _ClassVar[int]
    PACKAGINGSTYLE_FIELD_NUMBER: _ClassVar[int]
    NOUPCAVAILABLE_FIELD_NUMBER: _ClassVar[int]
    upc: str
    productName: str
    productCategory: str
    variantLabel: str
    packCount: int
    netQuantity: float
    quantityUnit: ProductUnit
    isVariableWeight: bool
    updatedAt: str
    brand: str
    flavor: str
    packagingStyle: PackagingStyle
    noUpcAvailable: bool
    def __init__(self, upc: _Optional[str] = ..., productName: _Optional[str] = ..., productCategory: _Optional[str] = ..., variantLabel: _Optional[str] = ..., packCount: _Optional[int] = ..., netQuantity: _Optional[float] = ..., quantityUnit: _Optional[_Union[ProductUnit, str]] = ..., isVariableWeight: bool = ..., updatedAt: _Optional[str] = ..., brand: _Optional[str] = ..., flavor: _Optional[str] = ..., packagingStyle: _Optional[_Union[PackagingStyle, str]] = ..., noUpcAvailable: bool = ...) -> None: ...

class UpcResponse(_message.Message):
    __slots__ = ("found", "info")
    FOUND_FIELD_NUMBER: _ClassVar[int]
    INFO_FIELD_NUMBER: _ClassVar[int]
    found: bool
    info: UpcInfo
    def __init__(self, found: bool = ..., info: _Optional[_Union[UpcInfo, _Mapping]] = ...) -> None: ...

class ProductInfo(_message.Message):
    __slots__ = ("productId", "productName", "productCategory", "updatedAt")
    PRODUCTID_FIELD_NUMBER: _ClassVar[int]
    PRODUCTNAME_FIELD_NUMBER: _ClassVar[int]
    PRODUCTCATEGORY_FIELD_NUMBER: _ClassVar[int]
    UPDATEDAT_FIELD_NUMBER: _ClassVar[int]
    productId: int
    productName: str
    productCategory: str
    updatedAt: str
    def __init__(self, productId: _Optional[int] = ..., productName: _Optional[str] = ..., productCategory: _Optional[str] = ..., updatedAt: _Optional[str] = ...) -> None: ...

class ListProductsRequest(_message.Message):
    __slots__ = ("updatedAfter",)
    UPDATEDAFTER_FIELD_NUMBER: _ClassVar[int]
    updatedAfter: str
    def __init__(self, updatedAfter: _Optional[str] = ...) -> None: ...

class ListProductsResponse(_message.Message):
    __slots__ = ("products", "nextSyncToken")
    PRODUCTS_FIELD_NUMBER: _ClassVar[int]
    NEXTSYNCTOKEN_FIELD_NUMBER: _ClassVar[int]
    products: _containers.RepeatedCompositeFieldContainer[ProductInfo]
    nextSyncToken: str
    def __init__(self, products: _Optional[_Iterable[_Union[ProductInfo, _Mapping]]] = ..., nextSyncToken: _Optional[str] = ...) -> None: ...

class ListVariantsForProductRequest(_message.Message):
    __slots__ = ("productName", "updatedAfter")
    PRODUCTNAME_FIELD_NUMBER: _ClassVar[int]
    UPDATEDAFTER_FIELD_NUMBER: _ClassVar[int]
    productName: str
    updatedAfter: str
    def __init__(self, productName: _Optional[str] = ..., updatedAfter: _Optional[str] = ...) -> None: ...

class ListVariantsForProductResponse(_message.Message):
    __slots__ = ("variants", "nextSyncToken")
    VARIANTS_FIELD_NUMBER: _ClassVar[int]
    NEXTSYNCTOKEN_FIELD_NUMBER: _ClassVar[int]
    variants: _containers.RepeatedCompositeFieldContainer[UpcInfo]
    nextSyncToken: str
    def __init__(self, variants: _Optional[_Iterable[_Union[UpcInfo, _Mapping]]] = ..., nextSyncToken: _Optional[str] = ...) -> None: ...

class StoreLookupRequest(_message.Message):
    __slots__ = ("storeAddress",)
    STOREADDRESS_FIELD_NUMBER: _ClassVar[int]
    storeAddress: str
    def __init__(self, storeAddress: _Optional[str] = ...) -> None: ...

class StoreLookupResponse(_message.Message):
    __slots__ = ("found", "store")
    FOUND_FIELD_NUMBER: _ClassVar[int]
    STORE_FIELD_NUMBER: _ClassVar[int]
    found: bool
    store: StoreInfo
    def __init__(self, found: bool = ..., store: _Optional[_Union[StoreInfo, _Mapping]] = ...) -> None: ...

class Coordinate(_message.Message):
    __slots__ = ("latitude", "longitude")
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    latitude: float
    longitude: float
    def __init__(self, latitude: _Optional[float] = ..., longitude: _Optional[float] = ...) -> None: ...

class StoreInfo(_message.Message):
    __slots__ = ("storeAddress", "location", "storeName", "requiresPaidMembership")
    STOREADDRESS_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    STORENAME_FIELD_NUMBER: _ClassVar[int]
    REQUIRESPAIDMEMBERSHIP_FIELD_NUMBER: _ClassVar[int]
    storeAddress: str
    location: Coordinate
    storeName: str
    requiresPaidMembership: bool
    def __init__(self, storeAddress: _Optional[str] = ..., location: _Optional[_Union[Coordinate, _Mapping]] = ..., storeName: _Optional[str] = ..., requiresPaidMembership: bool = ...) -> None: ...

class SaleInfo(_message.Message):
    __slots__ = ("startDate", "expirationDate", "minimumQuantity", "limitQuantity", "requiresPaidMembership", "requiresLoyaltyCard", "multipleOf")
    STARTDATE_FIELD_NUMBER: _ClassVar[int]
    EXPIRATIONDATE_FIELD_NUMBER: _ClassVar[int]
    MINIMUMQUANTITY_FIELD_NUMBER: _ClassVar[int]
    LIMITQUANTITY_FIELD_NUMBER: _ClassVar[int]
    REQUIRESPAIDMEMBERSHIP_FIELD_NUMBER: _ClassVar[int]
    REQUIRESLOYALTYCARD_FIELD_NUMBER: _ClassVar[int]
    MULTIPLEOF_FIELD_NUMBER: _ClassVar[int]
    startDate: str
    expirationDate: str
    minimumQuantity: int
    limitQuantity: int
    requiresPaidMembership: bool
    requiresLoyaltyCard: bool
    multipleOf: int
    def __init__(self, startDate: _Optional[str] = ..., expirationDate: _Optional[str] = ..., minimumQuantity: _Optional[int] = ..., limitQuantity: _Optional[int] = ..., requiresPaidMembership: bool = ..., requiresLoyaltyCard: bool = ..., multipleOf: _Optional[int] = ...) -> None: ...

class PriceObservationRequest(_message.Message):
    __slots__ = ("store", "upc", "priceTotal", "observedAt", "isSale", "saleInfo", "trainingImageJpeg", "trainingImageFilename", "trainingImageUpcPresent")
    STORE_FIELD_NUMBER: _ClassVar[int]
    UPC_FIELD_NUMBER: _ClassVar[int]
    PRICETOTAL_FIELD_NUMBER: _ClassVar[int]
    OBSERVEDAT_FIELD_NUMBER: _ClassVar[int]
    ISSALE_FIELD_NUMBER: _ClassVar[int]
    SALEINFO_FIELD_NUMBER: _ClassVar[int]
    TRAININGIMAGEJPEG_FIELD_NUMBER: _ClassVar[int]
    TRAININGIMAGEFILENAME_FIELD_NUMBER: _ClassVar[int]
    TRAININGIMAGEUPCPRESENT_FIELD_NUMBER: _ClassVar[int]
    store: StoreInfo
    upc: UpcInfo
    priceTotal: float
    observedAt: str
    isSale: bool
    saleInfo: SaleInfo
    trainingImageJpeg: bytes
    trainingImageFilename: str
    trainingImageUpcPresent: bool
    def __init__(self, store: _Optional[_Union[StoreInfo, _Mapping]] = ..., upc: _Optional[_Union[UpcInfo, _Mapping]] = ..., priceTotal: _Optional[float] = ..., observedAt: _Optional[str] = ..., isSale: bool = ..., saleInfo: _Optional[_Union[SaleInfo, _Mapping]] = ..., trainingImageJpeg: _Optional[bytes] = ..., trainingImageFilename: _Optional[str] = ..., trainingImageUpcPresent: bool = ...) -> None: ...

class PriceObservationResponse(_message.Message):
    __slots__ = ("observationId",)
    OBSERVATIONID_FIELD_NUMBER: _ClassVar[int]
    observationId: int
    def __init__(self, observationId: _Optional[int] = ...) -> None: ...

class ParsePriceTagImageRequest(_message.Message):
    __slots__ = ("imageJpeg", "imageFilename")
    IMAGEJPEG_FIELD_NUMBER: _ClassVar[int]
    IMAGEFILENAME_FIELD_NUMBER: _ClassVar[int]
    imageJpeg: bytes
    imageFilename: str
    def __init__(self, imageJpeg: _Optional[bytes] = ..., imageFilename: _Optional[str] = ...) -> None: ...

class ParsePriceTagImageResponse(_message.Message):
    __slots__ = ("ambiguous", "unparsable", "upcParsable", "upc", "priceTotal", "packCount", "netQuantity", "quantityUnit", "isVariableWeight", "message")
    AMBIGUOUS_FIELD_NUMBER: _ClassVar[int]
    UNPARSABLE_FIELD_NUMBER: _ClassVar[int]
    UPCPARSABLE_FIELD_NUMBER: _ClassVar[int]
    UPC_FIELD_NUMBER: _ClassVar[int]
    PRICETOTAL_FIELD_NUMBER: _ClassVar[int]
    PACKCOUNT_FIELD_NUMBER: _ClassVar[int]
    NETQUANTITY_FIELD_NUMBER: _ClassVar[int]
    QUANTITYUNIT_FIELD_NUMBER: _ClassVar[int]
    ISVARIABLEWEIGHT_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ambiguous: bool
    unparsable: bool
    upcParsable: bool
    upc: str
    priceTotal: float
    packCount: int
    netQuantity: float
    quantityUnit: ProductUnit
    isVariableWeight: bool
    message: str
    def __init__(self, ambiguous: bool = ..., unparsable: bool = ..., upcParsable: bool = ..., upc: _Optional[str] = ..., priceTotal: _Optional[float] = ..., packCount: _Optional[int] = ..., netQuantity: _Optional[float] = ..., quantityUnit: _Optional[_Union[ProductUnit, str]] = ..., isVariableWeight: bool = ..., message: _Optional[str] = ...) -> None: ...

class GroceryListOptimizationItem(_message.Message):
    __slots__ = ("itemId", "productName", "desiredCount", "comparisonMode", "preferredUpc", "desiredQuantityUnit")
    ITEMID_FIELD_NUMBER: _ClassVar[int]
    PRODUCTNAME_FIELD_NUMBER: _ClassVar[int]
    DESIREDCOUNT_FIELD_NUMBER: _ClassVar[int]
    COMPARISONMODE_FIELD_NUMBER: _ClassVar[int]
    PREFERREDUPC_FIELD_NUMBER: _ClassVar[int]
    DESIREDQUANTITYUNIT_FIELD_NUMBER: _ClassVar[int]
    itemId: int
    productName: str
    desiredCount: float
    comparisonMode: ComparisonMode
    preferredUpc: str
    desiredQuantityUnit: ProductUnit
    def __init__(self, itemId: _Optional[int] = ..., productName: _Optional[str] = ..., desiredCount: _Optional[float] = ..., comparisonMode: _Optional[_Union[ComparisonMode, str]] = ..., preferredUpc: _Optional[str] = ..., desiredQuantityUnit: _Optional[_Union[ProductUnit, str]] = ...) -> None: ...

class OptimizeGroceryListRequest(_message.Message):
    __slots__ = ("items", "allowPaidMembershipRequired", "allowLoyaltyCardRequired", "singleStoreOnly")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    ALLOWPAIDMEMBERSHIPREQUIRED_FIELD_NUMBER: _ClassVar[int]
    ALLOWLOYALTYCARDREQUIRED_FIELD_NUMBER: _ClassVar[int]
    SINGLESTOREONLY_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[GroceryListOptimizationItem]
    allowPaidMembershipRequired: bool
    allowLoyaltyCardRequired: bool
    singleStoreOnly: bool
    def __init__(self, items: _Optional[_Iterable[_Union[GroceryListOptimizationItem, _Mapping]]] = ..., allowPaidMembershipRequired: bool = ..., allowLoyaltyCardRequired: bool = ..., singleStoreOnly: bool = ...) -> None: ...

class OptimizedStore(_message.Message):
    __slots__ = ("storeId", "storeName", "storeAddress", "location", "requiresPaidMembership")
    STOREID_FIELD_NUMBER: _ClassVar[int]
    STORENAME_FIELD_NUMBER: _ClassVar[int]
    STOREADDRESS_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    REQUIRESPAIDMEMBERSHIP_FIELD_NUMBER: _ClassVar[int]
    storeId: int
    storeName: str
    storeAddress: str
    location: Coordinate
    requiresPaidMembership: bool
    def __init__(self, storeId: _Optional[int] = ..., storeName: _Optional[str] = ..., storeAddress: _Optional[str] = ..., location: _Optional[_Union[Coordinate, _Mapping]] = ..., requiresPaidMembership: bool = ...) -> None: ...

class OptimizedVariant(_message.Message):
    __slots__ = ("upc", "productName", "variantLabel", "packCount", "netQuantity", "quantityUnit", "brand", "flavor", "packagingStyle")
    UPC_FIELD_NUMBER: _ClassVar[int]
    PRODUCTNAME_FIELD_NUMBER: _ClassVar[int]
    VARIANTLABEL_FIELD_NUMBER: _ClassVar[int]
    PACKCOUNT_FIELD_NUMBER: _ClassVar[int]
    NETQUANTITY_FIELD_NUMBER: _ClassVar[int]
    QUANTITYUNIT_FIELD_NUMBER: _ClassVar[int]
    BRAND_FIELD_NUMBER: _ClassVar[int]
    FLAVOR_FIELD_NUMBER: _ClassVar[int]
    PACKAGINGSTYLE_FIELD_NUMBER: _ClassVar[int]
    upc: str
    productName: str
    variantLabel: str
    packCount: int
    netQuantity: float
    quantityUnit: ProductUnit
    brand: str
    flavor: str
    packagingStyle: PackagingStyle
    def __init__(self, upc: _Optional[str] = ..., productName: _Optional[str] = ..., variantLabel: _Optional[str] = ..., packCount: _Optional[int] = ..., netQuantity: _Optional[float] = ..., quantityUnit: _Optional[_Union[ProductUnit, str]] = ..., brand: _Optional[str] = ..., flavor: _Optional[str] = ..., packagingStyle: _Optional[_Union[PackagingStyle, str]] = ...) -> None: ...

class OptimizedItemMatch(_message.Message):
    __slots__ = ("itemId", "comparisonMode", "desiredCount", "store", "variant", "priceObservationId", "observedPriceTotal", "observedAt", "estimatedTotalPrice", "requiresPaidMembership", "requiresLoyaltyCard", "pricingBasisLine", "pricingEquationLine", "approximationWarning")
    ITEMID_FIELD_NUMBER: _ClassVar[int]
    COMPARISONMODE_FIELD_NUMBER: _ClassVar[int]
    DESIREDCOUNT_FIELD_NUMBER: _ClassVar[int]
    STORE_FIELD_NUMBER: _ClassVar[int]
    VARIANT_FIELD_NUMBER: _ClassVar[int]
    PRICEOBSERVATIONID_FIELD_NUMBER: _ClassVar[int]
    OBSERVEDPRICETOTAL_FIELD_NUMBER: _ClassVar[int]
    OBSERVEDAT_FIELD_NUMBER: _ClassVar[int]
    ESTIMATEDTOTALPRICE_FIELD_NUMBER: _ClassVar[int]
    REQUIRESPAIDMEMBERSHIP_FIELD_NUMBER: _ClassVar[int]
    REQUIRESLOYALTYCARD_FIELD_NUMBER: _ClassVar[int]
    PRICINGBASISLINE_FIELD_NUMBER: _ClassVar[int]
    PRICINGEQUATIONLINE_FIELD_NUMBER: _ClassVar[int]
    APPROXIMATIONWARNING_FIELD_NUMBER: _ClassVar[int]
    itemId: int
    comparisonMode: ComparisonMode
    desiredCount: float
    store: OptimizedStore
    variant: OptimizedVariant
    priceObservationId: int
    observedPriceTotal: float
    observedAt: str
    estimatedTotalPrice: float
    requiresPaidMembership: bool
    requiresLoyaltyCard: bool
    pricingBasisLine: str
    pricingEquationLine: str
    approximationWarning: str
    def __init__(self, itemId: _Optional[int] = ..., comparisonMode: _Optional[_Union[ComparisonMode, str]] = ..., desiredCount: _Optional[float] = ..., store: _Optional[_Union[OptimizedStore, _Mapping]] = ..., variant: _Optional[_Union[OptimizedVariant, _Mapping]] = ..., priceObservationId: _Optional[int] = ..., observedPriceTotal: _Optional[float] = ..., observedAt: _Optional[str] = ..., estimatedTotalPrice: _Optional[float] = ..., requiresPaidMembership: bool = ..., requiresLoyaltyCard: bool = ..., pricingBasisLine: _Optional[str] = ..., pricingEquationLine: _Optional[str] = ..., approximationWarning: _Optional[str] = ...) -> None: ...

class UnmatchedOptimizationItem(_message.Message):
    __slots__ = ("itemId", "productName", "reason")
    ITEMID_FIELD_NUMBER: _ClassVar[int]
    PRODUCTNAME_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    itemId: int
    productName: str
    reason: str
    def __init__(self, itemId: _Optional[int] = ..., productName: _Optional[str] = ..., reason: _Optional[str] = ...) -> None: ...

class OptimizeGroceryListResponse(_message.Message):
    __slots__ = ("matches", "unmatched")
    MATCHES_FIELD_NUMBER: _ClassVar[int]
    UNMATCHED_FIELD_NUMBER: _ClassVar[int]
    matches: _containers.RepeatedCompositeFieldContainer[OptimizedItemMatch]
    unmatched: _containers.RepeatedCompositeFieldContainer[UnmatchedOptimizationItem]
    def __init__(self, matches: _Optional[_Iterable[_Union[OptimizedItemMatch, _Mapping]]] = ..., unmatched: _Optional[_Iterable[_Union[UnmatchedOptimizationItem, _Mapping]]] = ...) -> None: ...
