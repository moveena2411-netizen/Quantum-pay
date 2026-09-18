from datetime import datetime

from pydantic import BaseModel
from pydantic import EmailStr


# =========================================================
# REGISTER REQUEST
# =========================================================

class UserCreate(BaseModel):

    name: str

    email: EmailStr

    phone: str

    password: str


# =========================================================
# USER RESPONSE
# =========================================================

class UserResponse(BaseModel):

    id: int

    name: str

    email: EmailStr

    phone: str

    class Config:
        from_attributes = True


# =========================================================
# LOGIN REQUEST
# =========================================================

class LoginRequest(BaseModel):

    email: EmailStr

    password: str


# =========================================================
# LOGIN RESPONSE
# =========================================================

class LoginResponse(BaseModel):

    message: str

    user_id: int

    name: str

    email: EmailStr


# =========================================================
# SEND MONEY REQUEST
# =========================================================

class SendMoneyRequest(BaseModel):

    sender_id: int

    receiver: str

    amount: float


# =========================================================
# RECEIVE MONEY REQUEST
# =========================================================

class ReceiveMoneyRequest(BaseModel):

    user_id: int

    amount: float


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