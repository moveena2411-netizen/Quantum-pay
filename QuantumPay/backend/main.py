from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException

from sqlalchemy.orm import Session

from database import Base
from database import engine
from database import get_db

import models
import schemas

from security import hash_password
from security import verify_password


# =========================================================
# CREATE DATABASE TABLES
# =========================================================

Base.metadata.create_all(bind=engine)


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="QuantumPay API",
    description="Backend API for the QuantumPay application",
    version="1.0.0",
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "message": "QuantumPay Backend is running",
        "status": "success"
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "QuantumPay API"
    }


# =========================================================
# DATABASE TEST
# =========================================================

@app.get("/database-test")
def database_test():
    return {
        "message": "Database connection is configured",
        "database": "SQLite",
        "status": "success"
    }


# =========================================================
# REGISTER USER
# =========================================================

@app.post(
    "/register",
    response_model=schemas.UserResponse
)
def register_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):

    # Check email
    existing_email = (
        db.query(models.User)
        .filter(models.User.email == user.email)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Check phone
    existing_phone = (
        db.query(models.User)
        .filter(models.User.phone == user.phone)
        .first()
    )

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Phone number already registered"
        )

    # Hash password
    hashed_password = hash_password(user.password)

    # Create user
    new_user = models.User(
        name=user.name,
        email=user.email,
        phone=user.phone,
        password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create wallet
    new_wallet = models.Wallet(
        user_id=new_user.id,
        balance=25000.0
    )

    db.add(new_wallet)
    db.commit()

    return new_user


# =========================================================
# LOGIN USER
# =========================================================

@app.post(
    "/login",
    response_model=schemas.LoginResponse
)
def login_user(
    user: schemas.LoginRequest,
    db: Session = Depends(get_db)
):

    existing_user = (
        db.query(models.User)
        .filter(models.User.email == user.email)
        .first()
    )

    if existing_user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    password_correct = verify_password(
        user.password,
        existing_user.password
    )

    if not password_correct:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    return {
        "message": "Login successful",
        "user_id": existing_user.id,
        "name": existing_user.name,
        "email": existing_user.email
    }


# =========================================================
# GET WALLET BALANCE
# =========================================================

@app.get("/wallet/{user_id}")
def get_wallet(
    user_id: int,
    db: Session = Depends(get_db)
):

    wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.user_id == user_id)
        .first()
    )

    if wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Wallet not found"
        )

    return {
        "user_id": user_id,
        "balance": wallet.balance
    }


# =========================================================
# SEND MONEY
# =========================================================

@app.post("/wallet/send")
def send_money(
    request: schemas.SendMoneyRequest,
    db: Session = Depends(get_db)
):

    # Find sender
    sender = (
        db.query(models.User)
        .filter(models.User.id == request.sender_id)
        .first()
    )

    if sender is None:
        raise HTTPException(
            status_code=404,
            detail="Sender not found"
        )

    # Check amount
    if request.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be greater than zero"
        )

    # Find sender wallet
    sender_wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.user_id == request.sender_id)
        .first()
    )

    if sender_wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Sender wallet not found"
        )

    # Check balance
    if sender_wallet.balance < request.amount:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance"
        )

    # Find receiver by email or phone
    receiver = (
        db.query(models.User)
        .filter(
            (models.User.email == request.receiver) |
            (models.User.phone == request.receiver)
        )
        .first()
    )

    if receiver is None:
        raise HTTPException(
            status_code=404,
            detail="Receiver not found"
        )

    # Prevent sending to yourself
    if receiver.id == sender.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot send money to yourself"
        )

    # Find receiver wallet
    receiver_wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.user_id == receiver.id)
        .first()
    )

    if receiver_wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Receiver wallet not found"
        )

    # Transfer money
    sender_wallet.balance -= request.amount
    receiver_wallet.balance += request.amount

    # Create transaction
    transaction = models.Transaction(
        sender=sender.email,
        receiver=receiver.email,
        amount=request.amount,
        transaction_type="SEND"
    )

    db.add(transaction)

    # Save everything
    db.commit()

    return {
        "message": "Money sent successfully",
        "sender": sender.email,
        "receiver": receiver.email,
        "amount": request.amount,
        "sender_balance": sender_wallet.balance
    }


# =========================================================
# RECEIVE MONEY
# =========================================================

@app.post("/wallet/receive")
def receive_money(
    request: schemas.ReceiveMoneyRequest,
    db: Session = Depends(get_db)
):

    # Check amount
    if request.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be greater than zero"
        )

    # Find user
    user = (
        db.query(models.User)
        .filter(models.User.id == request.user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Find wallet
    wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.user_id == request.user_id)
        .first()
    )

    if wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Wallet not found"
        )

    # Increase balance
    wallet.balance += request.amount

    # Create transaction
    transaction = models.Transaction(
        sender="External",
        receiver=user.email,
        amount=request.amount,
        transaction_type="RECEIVE"
    )

    db.add(transaction)

    db.commit()

    return {
        "message": "Money received successfully",
        "user": user.email,
        "amount": request.amount,
        "balance": wallet.balance
    }


# =========================================================
# TRANSACTION HISTORY
# =========================================================

@app.get(
    "/transactions/{user_id}",
    response_model=list[schemas.TransactionResponse]
)
def get_transactions(
    user_id: int,
    db: Session = Depends(get_db)
):

    # Find user
    user = (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Get transactions involving this user
    transactions = (
        db.query(models.Transaction)
        .filter(
            (models.Transaction.sender == user.email) |
            (models.Transaction.receiver == user.email)
        )
        .order_by(
            models.Transaction.timestamp.desc()
        )
        .all()
    )

    return transactions