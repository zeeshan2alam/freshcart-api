import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import (BaseModel, ConfigDict, EmailStr, Field, field_serializer,
                      field_validator, model_validator)

Role = Literal["admin", "customer"]
Method = Literal["upi", "card", "cod"]
Theme = Literal["red", "orange", "green", "purple"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Stamped(ORM):
    created_at: datetime

    @field_serializer("created_at")
    def _utc(self, v: datetime) -> str:
        return v.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


# ---------- auth ----------
class RegisterIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class UserOut(ORM):
    id: int
    name: str
    email: str
    role: Role


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- products ----------
class ProductIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    category: str = Field(min_length=1, max_length=40)
    unit: str = Field(min_length=1, max_length=20)
    price: float = Field(ge=0, le=1_000_000)
    stock: int = Field(ge=0, le=1_000_000)
    emoji: str = Field(default="", max_length=8)


class ProductOut(Stamped):
    id: int
    name: str
    category: str
    unit: str
    price: float
    stock: int
    emoji: str


# ---------- offers ----------
class OfferIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=120)
    emoji: str = Field(default="", max_length=8)
    percent: int = Field(default=0, ge=0, le=90)
    code: str | None = Field(default=None, max_length=14)
    theme: Theme = "red"

    @field_validator("code")
    @classmethod
    def _code(cls, v: str | None) -> str | None:
        if not v:
            return None
        v = v.upper()
        if not re.fullmatch(r"[A-Z0-9]+", v):
            raise ValueError("Coupon code mein sirf letters aur numbers ho sakte hain")
        return v

    @model_validator(mode="after")
    def _needs_percent(self):
        if self.code and not self.percent:
            raise ValueError("Coupon code ke saath discount % bhi daalein")
        return self


class OfferPatch(BaseModel):
    active: bool


class OfferOut(Stamped):
    id: int
    text: str
    emoji: str
    percent: int
    code: str | None
    theme: str
    active: bool


class CouponIn(BaseModel):
    code: str = Field(max_length=14)


class CouponOut(BaseModel):
    valid: bool
    code: str
    percent: int = 0


# ---------- orders ----------
class OrderItemIn(BaseModel):
    product_id: int
    qty: int = Field(ge=1, le=100)


class OrderIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    items: list[OrderItemIn] = Field(min_length=1, max_length=50)
    customer_name: str = Field(min_length=2, max_length=80)
    phone: str
    address: str = Field(min_length=5, max_length=255)
    city: str = Field(min_length=1, max_length=60)
    pincode: str
    method: Method
    coupon: str | None = Field(default=None, max_length=14)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        if not re.fullmatch(r"[6-9]\d{9}", v):
            raise ValueError("Sahi 10-digit phone number daalein")
        return v

    @field_validator("pincode")
    @classmethod
    def _pin(cls, v: str) -> str:
        if not re.fullmatch(r"\d{6}", v):
            raise ValueError("Sahi 6-digit pincode daalein")
        return v


class OrderItemOut(ORM):
    product_id: int | None
    name: str
    unit: str
    price: float
    qty: int
    emoji: str


class OrderOut(Stamped):
    code: str
    user_email: str
    customer_name: str
    phone: str
    address: str
    city: str
    pincode: str
    items: list[OrderItemOut]
    subtotal: float
    discount: float
    coupon: str
    delivery: float
    total: float
    method: Method
    status: str
    is_sample: bool
