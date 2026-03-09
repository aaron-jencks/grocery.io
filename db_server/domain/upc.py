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
    TSP = 10
    TBSP = 11


class PackagingStyle(Enum):
    UNSPECIFIED = 0
    LOOSE = 1
    CAN = 2
    BOTTLE = 3
    BOX = 4
    BAG = 5
    CARTON = 6
    BUNCH = 7
    OTHER = 8


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
    brand: Optional[str]
    flavor: Optional[str]
    packaging_style: Optional[PackagingStyle]
    pack_count: int
    net_quantity: float
    quantity_unit: ProductUnit
    is_variable_weight: bool
    upc: str
    updated_at: str
