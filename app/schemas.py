import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any
from pydantic import BaseModel, Field, HttpUrl, field_validator

class PaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(..., min_length=3, max_length=3)
    description: str | None = Field(None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: HttpUrl

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        upper_v = v.upper()
        if upper_v not in ["RUB", "USD", "EUR"]:
            raise ValueError("Currency must be RUB, USD, or EUR")
        return upper_v

class PaymentResponse(BaseModel):
    id: uuid.UUID
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class PaymentDetailResponse(BaseModel):
    id: uuid.UUID
    amount: Decimal
    currency: str
    description: str | None
    metadata_json: dict[str, Any]
    status: str
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None

    class Config:
        from_attributes = True
        populate_by_name = True
