from __future__ import annotations

from pydantic import Field

from .base import BaleObject, BoundObject
from .chat import User


class LabeledPrice(BaleObject):
    label: str
    amount: int


class Invoice(BoundObject):
    title: str
    description: str
    total_amount: int


class SuccessfulPayment(BoundObject):
    currency: str
    total_amount: int
    invoice_payload: str
    telegram_payment_charge_id: str | None = None
    provider_payment_charge_id: str | None = None


class PreCheckoutQuery(BoundObject):
    id: str
    from_user: User = Field(alias="from")
    currency: str
    total_amount: int
    invoice_payload: str


class Transaction(BoundObject):
    id: str
    status: str
    userID: int | None = None
    amount: int | None = None
    createdAt: int | None = None


__all__ = [
    "Invoice",
    "LabeledPrice",
    "PreCheckoutQuery",
    "SuccessfulPayment",
    "Transaction",
]
