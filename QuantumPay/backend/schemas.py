from datetime import datetime
import re

from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 7:
            raise ValueError("Password must contain at least 7 characters")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError("Password must contain at least one special character")
        return value


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str | None = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    message: str
    user_id: int
    name: str
    email: EmailStr
    payment_pin_set: bool
    passkey_set: bool


class PaymentPinSetupRequest(BaseModel):
    user_id: int
    login_password: str
    payment_pin: str

    @field_validator("payment_pin")
    @classmethod
    def validate_payment_pin(cls, value: str) -> str:
        if not re.fullmatch(r"\d{6}", value):
            raise ValueError("Payment PIN must be exactly 6 digits")
        return value


class PaymentPinVerifyRequest(BaseModel):
    user_id: int
    payment_pin: str

    @field_validator("payment_pin")
    @classmethod
    def validate_payment_pin(cls, value: str) -> str:
        if not re.fullmatch(r"\d{6}", value):
            raise ValueError("Payment PIN must be exactly 6 digits")
        return value


class BalanceRequest(BaseModel):
    user_id: int
    payment_pin: str

    @field_validator("payment_pin")
    @classmethod
    def validate_payment_pin(cls, value: str) -> str:
        if not re.fullmatch(r"\d{6}", value):
            raise ValueError("Payment PIN must be exactly 6 digits")
        return value


class RiskContext(BaseModel):
    # These are backend security-context signals, NOT the outgoing payment message.
    suspicious_message: bool = False
    suspicious_payment_identifier: bool = False
    location_changed: bool = False
    network_changed: bool = False
    new_device: bool = False
    failed_authentication_attempts: int = 0
    previous_suspicious_activity: bool = False
    receiver_reports: int = 0
    unusual_payment_instruction: bool = False


class SendMoneyRequest(BaseModel):
    sender_id: int
    receiver: str
    amount: float
    payment_pin: str
    # Optional transaction information only. Never used for risk analysis.
    message: str = ""
    risk_context: RiskContext | None = None

    @field_validator("payment_pin")
    @classmethod
    def validate_payment_pin(cls, value: str) -> str:
        if not re.fullmatch(r"\d{6}", value):
            raise ValueError("Payment PIN must be exactly 6 digits")
        return value


class ReceiveMoneyRequest(BaseModel):
    user_id: int
    amount: float


class TransactionResponse(BaseModel):
    id: int
    sender: str
    receiver: str
    amount: float
    transaction_type: str
    timestamp: datetime

    class Config:
        from_attributes = True


class ChallengeAnswersRequest(BaseModel):
    answers: dict[str, bool]


class ChallengeCompletionRequest(BaseModel):
    pending_transaction_id: int
    answers: dict[str, bool]
    payment_pin: str

    @field_validator("payment_pin")
    @classmethod
    def validate_payment_pin(cls, value: str) -> str:
        if not re.fullmatch(r"\d{6}", value):
            raise ValueError("Payment PIN must be exactly 6 digits")
        return value


class IncomingSecurityMessageRequest(BaseModel):
    sender_phone: str
    message_text: str
