from dataclasses import dataclass
import datetime as dt
from typing import Optional

from db_server.domain.upc import ProductVariant


@dataclass
class Sale:
    rowid: int
    limit_quantity: Optional[int]
    expiration_date: Optional[dt.datetime]
    start_date: dt.datetime
    minimum_quantity: Optional[int]
    multiple_of: Optional[int]
    requires_paid_membership: bool
    requires_loyalty_card: bool


@dataclass
class Store:
    rowid: int
    name: Optional[str]
    address: str
    latitude: Optional[float]
    longitude: Optional[float]
    requires_paid_membership: bool


@dataclass
class PriceObservation:
    rowid: int
    store: Store
    variant: ProductVariant
    price_total: float
    observed_at: dt.datetime
    sale: Optional[Sale]
