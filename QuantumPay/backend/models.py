from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String

from database import Base


# =========================================================
# USER TABLE
# =========================================================

class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    email = Column(String(150), unique=True, index=True, nullable=False)

    phone = Column(String(20), unique=True, nullable=True)

    # Stores the secure hash of the login password.
    password = Column(String(255), nullable=False)


# =========================================================
# WALLET TABLE
# =========================================================

class Wallet(Base):

    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )

    balance = Column(Float, default=0.0, nullable=False)


# =========================================================
# TRANSACTION TABLE
# =========================================================

class Transaction(Base):

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    sender = Column(String(150), nullable=False)

    receiver = Column(String(150), nullable=False)

    amount = Column(Float, nullable=False)

    transaction_type = Column(String(20), nullable=False)

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)


# =========================================================
# PAYMENT PIN TABLE
# =========================================================

class PaymentCredential(Base):

    __tablename__ = "payment_credentials"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Never store the 6-digit PIN itself.
    pin_hash = Column(String(255), nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
