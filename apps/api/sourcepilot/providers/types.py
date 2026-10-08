import ipaddress
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, field_validator


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

    @field_validator("supplier_website", "source_url")
    @classmethod
    def public_http_url(cls, value: HttpUrl) -> HttpUrl:
        host = urlparse(str(value)).hostname
        if host in {"localhost", "localhost.localdomain"}:
            raise ValueError("external evidence URL cannot target localhost")
        try:
            address = ipaddress.ip_address(host or "")
        except ValueError:
            return value
        if not address.is_global:
            raise ValueError("external evidence URL must use a public address")
        return value


class LLMMessage(BaseModel):
    role: str
    content: str
