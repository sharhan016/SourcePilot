from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class SearchDocument(BaseModel):
    title: str
    url: HttpUrl
    content: str = ""
    provider: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductCandidate(BaseModel):
    supplier_name: str
    supplier_website: HttpUrl
    supplier_location: str | None = None
    supplier_type: str | None = None
    product_name: str
    manufacturer: str | None = None
    model: str | None = None
    specifications: dict[str, Any] = Field(default_factory=dict)
    unit_price: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    available_quantity: int | None = Field(default=None, ge=0)
    availability: str | None = None
    warranty: str | None = None
    delivery: str | None = None
    source_url: HttpUrl
    source_type: str = "web"
    is_first_party: bool = False


class LLMMessage(BaseModel):
    role: str
    content: str
