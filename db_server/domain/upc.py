from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ProductUnit(Enum):
    OZ = 0
    LB = 1
    EA = 2
    KG = 3
    G = 4
    LIT = 5
    ML = 6
    GAL = 7
    QT = 8
    PT = 9


@dataclass
class Product:
    rowid: int
    name: str
    category: Optional[str]
    updated_at: str


@dataclass
class ProductVariant:
    rowid: int
    product: Product
    label: str
    pack_count: int
    net_quantity: float
    quantity_unit: ProductUnit
    is_variable_weight: bool
    upc: str
    updated_at: str
