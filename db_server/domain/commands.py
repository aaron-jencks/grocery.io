from dataclasses import dataclass
from typing import Optional

from db_server.domain.upc import PackagingStyle, ProductUnit


@dataclass
class SaleInput:
    start_date: str
    expiration_date: Optional[str] = None
    minimum_quantity: Optional[int] = None
    limit_quantity: Optional[int] = None
    multiple_of: Optional[int] = None
    requires_paid_membership: bool = False
    requires_loyalty_card: bool = False


@dataclass
class PriceObservationInput:
    store_address: str
    store_latitude: Optional[float]
    store_longitude: Optional[float]
    store_name: Optional[str]
    upc: str
    product_name: str
    product_category: Optional[str]
    variant_label: str
    pack_count: int
    net_quantity: float
    quantity_unit: ProductUnit
    is_variable_weight: bool
    price_total: float
    observed_at: str
    is_sale: bool
    sale: Optional[SaleInput] = None
    store_requires_paid_membership: bool = False
    brand: Optional[str] = None
    flavor: Optional[str] = None
    packaging_style: Optional[PackagingStyle] = None
