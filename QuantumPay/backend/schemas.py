from datetime import datetime
import re

from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import field_validator


# =========================================================
# REGISTER REQUEST
# =========================================================

class UserCreate(BaseModel):

    name: str
    email: EmailStr
    phone: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 7:
            raise ValueError(
                "Password must contain at least 7 characters"
            )

        if not re.search(r"[A-Z]", value):
            raise ValueError(
                "Password must contain at least one uppercase letter"
            )

        if not re.search(r"[a-z]", value):
            raise ValueError(
                "Password must contain at least one lowercase letter"
            )

        if not re.search(r"\d", value):
            raise ValueError(
                "Password must contain at least one digit"
            )

        if not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError(
                "Password must contain at least one special character"
            )

        return value


# =========================================================
# USER RESPONSE
# =========================================================

class UserResponse(BaseModel):

    id: int
    name: str
    email: EmailStr
    phone: str | None = None

    class Config:
        from_attributes = True


# =========================================================
# LOGIN REQUEST / RESPONSE
# =========================================================

class LoginRequest(BaseModel):

    email: EmailStr
    password: str


class LoginResponse(BaseModel):

    message: str
    user_id: int
    name: str
    email: EmailStr
    payment_pin_set: bool


# =========================================================
# PAYMENT PIN SETUP
# =========================================================

class PaymentPinSetupRequest(BaseModel):

    user_id: int
    login_password: str
    payment_pin: str

    @field_validator("payment_pin")
    @classmethod
    def validate_payment_pin(cls, value: str) -> str:
        if not re.fullmatch(r"\d{6}", value):
            raise ValueError(
                "Payment PIN must be exactly 6 digits"
            )
        return value


# =========================================================
# PAYMENT PIN VERIFICATION
# =========================================================

class PaymentPinVerifyRequest(BaseModel):

    user_id: int
    payment_pin: str

    @field_validator("payment_pin")
    @classmethod
    def validate_payment_pin(cls, value: str) -> str:
        if not re.fullmatch(r"\d{6}", value):
            raise ValueError(
                "Payment PIN must be exactly 6 digits"
            )
        return value


# =========================================================
# BALANCE
# =========================================================

class BalanceRequest(BaseModel):

    user_id: int
    payment_pin: str

    @field_validator("payment_pin")
    @classmethod
    def validate_payment_pin(cls, value: str) -> str:
        if not re.fullmatch(r"\d{6}", value):
            raise ValueError(
                "Payment PIN must be exactly 6 digits"
            )
        return value


# =========================================================
# SEND MONEY
# =========================================================

class SendMoneyRequest(BaseModel):

    sender_id: int
    receiver: str
    amount: float
    payment_pin: str

    @field_validator("payment_pin")
    @classmethod
    def validate_payment_pin(cls, value: str) -> str:
        if not re.fullmatch(r"\d{6}", value):
            raise ValueError(
                "Payment PIN must be exactly 6 digits"
            )
        return value


# =========================================================
# TRANSACTION RESPONSE
# =========================================================

class TransactionResponse(BaseModel):

    id: int
    sender: str
    receiver: str
    amount: float
    transaction_type: str
    timestamp: datetime

    class Config:
        from_attributes = True
