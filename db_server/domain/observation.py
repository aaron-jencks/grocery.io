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


@dataclass
class Store:
    rowid: int
    name: Optional[str]
    address: str
    latitude: float
    longitude: float


@dataclass
class PriceObservation:
    rowid: int
    store: Store
    variant: ProductVariant
    price_total: float
    observed_at: dt.datetime
    sale: Optional[Sale]
