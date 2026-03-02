from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ProductUnit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    OZ: _ClassVar[ProductUnit]
    LB: _ClassVar[ProductUnit]
    EA: _ClassVar[ProductUnit]
    KG: _ClassVar[ProductUnit]
    G: _ClassVar[ProductUnit]
    LIT: _ClassVar[ProductUnit]
    ML: _ClassVar[ProductUnit]
    GAL: _ClassVar[ProductUnit]
    QT: _ClassVar[ProductUnit]
    PT: _ClassVar[ProductUnit]
OZ: ProductUnit
LB: ProductUnit
EA: ProductUnit
KG: ProductUnit
G: ProductUnit
LIT: ProductUnit
ML: ProductUnit
GAL: ProductUnit
QT: ProductUnit
PT: ProductUnit

class UpcRequest(_message.Message):
    __slots__ = ("upc",)
    UPC_FIELD_NUMBER: _ClassVar[int]
    upc: str
    def __init__(self, upc: _Optional[str] = ...) -> None: ...

class UpcInfo(_message.Message):
    __slots__ = ("upc", "productName", "productCategory", "variantLabel", "packCount", "netQuantity", "quantityUnit", "isVariableWeight")
    UPC_FIELD_NUMBER: _ClassVar[int]
    PRODUCTNAME_FIELD_NUMBER: _ClassVar[int]
    PRODUCTCATEGORY_FIELD_NUMBER: _ClassVar[int]
    VARIANTLABEL_FIELD_NUMBER: _ClassVar[int]
    PACKCOUNT_FIELD_NUMBER: _ClassVar[int]
    NETQUANTITY_FIELD_NUMBER: _ClassVar[int]
    QUANTITYUNIT_FIELD_NUMBER: _ClassVar[int]
    ISVARIABLEWEIGHT_FIELD_NUMBER: _ClassVar[int]
    upc: str
    productName: str
    productCategory: str
    variantLabel: str
    packCount: int
    netQuantity: float
    quantityUnit: ProductUnit
    isVariableWeight: bool
    def __init__(self, upc: _Optional[str] = ..., productName: _Optional[str] = ..., productCategory: _Optional[str] = ..., variantLabel: _Optional[str] = ..., packCount: _Optional[int] = ..., netQuantity: _Optional[float] = ..., quantityUnit: _Optional[_Union[ProductUnit, str]] = ..., isVariableWeight: bool = ...) -> None: ...

class UpcResponse(_message.Message):
    __slots__ = ("found", "info")
    FOUND_FIELD_NUMBER: _ClassVar[int]
    INFO_FIELD_NUMBER: _ClassVar[int]
    found: bool
    info: UpcInfo
    def __init__(self, found: bool = ..., info: _Optional[_Union[UpcInfo, _Mapping]] = ...) -> None: ...

class Coordinate(_message.Message):
    __slots__ = ("latitude", "longitude")
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    latitude: float
    longitude: float
    def __init__(self, latitude: _Optional[float] = ..., longitude: _Optional[float] = ...) -> None: ...

class StoreInfo(_message.Message):
    __slots__ = ("storeAddress", "location", "storeName")
    STOREADDRESS_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    STORENAME_FIELD_NUMBER: _ClassVar[int]
    storeAddress: str
    location: Coordinate
    storeName: str
    def __init__(self, storeAddress: _Optional[str] = ..., location: _Optional[_Union[Coordinate, _Mapping]] = ..., storeName: _Optional[str] = ...) -> None: ...

class SaleInfo(_message.Message):
    __slots__ = ("startDate", "expirationDate", "minimumQuantity", "limitQuantity")
    STARTDATE_FIELD_NUMBER: _ClassVar[int]
    EXPIRATIONDATE_FIELD_NUMBER: _ClassVar[int]
    MINIMUMQUANTITY_FIELD_NUMBER: _ClassVar[int]
    LIMITQUANTITY_FIELD_NUMBER: _ClassVar[int]
    startDate: str
    expirationDate: str
    minimumQuantity: int
    limitQuantity: int
    def __init__(self, startDate: _Optional[str] = ..., expirationDate: _Optional[str] = ..., minimumQuantity: _Optional[int] = ..., limitQuantity: _Optional[int] = ...) -> None: ...

class PriceObservationRequest(_message.Message):
    __slots__ = ("store", "upc", "priceTotal", "observedAt", "isSale", "saleInfo")
    STORE_FIELD_NUMBER: _ClassVar[int]
    UPC_FIELD_NUMBER: _ClassVar[int]
    PRICETOTAL_FIELD_NUMBER: _ClassVar[int]
    OBSERVEDAT_FIELD_NUMBER: _ClassVar[int]
    ISSALE_FIELD_NUMBER: _ClassVar[int]
    SALEINFO_FIELD_NUMBER: _ClassVar[int]
    store: StoreInfo
    upc: UpcInfo
    priceTotal: float
    observedAt: str
    isSale: bool
    saleInfo: SaleInfo
    def __init__(self, store: _Optional[_Union[StoreInfo, _Mapping]] = ..., upc: _Optional[_Union[UpcInfo, _Mapping]] = ..., priceTotal: _Optional[float] = ..., observedAt: _Optional[str] = ..., isSale: bool = ..., saleInfo: _Optional[_Union[SaleInfo, _Mapping]] = ...) -> None: ...

class PriceObservationResponse(_message.Message):
    __slots__ = ("observationId",)
    OBSERVATIONID_FIELD_NUMBER: _ClassVar[int]
    observationId: int
    def __init__(self, observationId: _Optional[int] = ...) -> None: ...
