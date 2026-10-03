from pathlib import Path
import secrets
from hmac import compare_digest
from datetime import datetime, timedelta, timezone
from security import hash_password, verify_password
from hash_utils import transaction_hash
import base64

from ml_dsa_security import sign_data, verify_signature
from ml_dsa_keys import get_or_create_keys
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session


from webauthn import (
    base64url_to_bytes,
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from database import Base, engine, get_db
import models
import passkey_models
import passkey_schemas
import schemas


# =========================================================
# PASSKEY LOGIN REQUEST MODELS
# =========================================================

class PasskeyAuthenticationOptionsRequest(BaseModel):
    email: str


class PasskeyAuthenticationVerifyRequest(BaseModel):
    state_id: int
    credential: dict


# =========================================================
# WEBAUTHN CONFIGURATION
# =========================================================

RP_ID = "squeak-crablike-walnut.ngrok-free.dev"
RP_NAME = "QuantumPay"
RP_ORIGIN = "https://squeak-crablike-walnut.ngrok-free.dev"
ANDROID_ORIGIN = (
    "android:apk-key-hash:qZ3BtXXH659fTEAZl3lY9JCnj1oFGSXGvo3cbCAGP_Y"
)
RP_ORIGINS = [RP_ORIGIN, ANDROID_ORIGIN]


# =========================================================
# DATABASE
# =========================================================

Base.metadata.create_all(bind=engine)


# =========================================================
# APPLICATION
# =========================================================

app = FastAPI(
    title="QuantumPay API",
    description="Backend API for the QuantumPay application",
    version="1.1.0",
)

BASE_DIR = Path(__file__).resolve().parent
ASSETLINKS_FILE = BASE_DIR / ".well-known" / "assetlinks.json"


# =========================================================
# ASSET LINKS
# =========================================================

@app.get("/.well-known/assetlinks.json", include_in_schema=False)
def assetlinks():
    if not ASSETLINKS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="assetlinks.json not found",
        )

    return FileResponse(
        path=ASSETLINKS_FILE,
        media_type="application/json",
    )


# =========================================================
# BASIC ENDPOINTS
# =========================================================

@app.get("/")
def root():
    return {
        "message": "QuantumPay Backend is running",
        "status": "success",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "QuantumPay API",
    }


@app.get("/database-test")
def database_test():
    return {
        "message": "Database connection is configured",
        "database": "SQLite",
        "status": "success",
    }


# =========================================================
# REGISTER USER
# =========================================================

@app.post("/register", response_model=schemas.UserResponse)
def register_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    existing_email = (
        db.query(models.User)
        .filter(models.User.email == user.email)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    existing_phone = (
        db.query(models.User)
        .filter(models.User.phone == user.phone)
        .first()
    )

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Phone number already registered",
        )

    new_user = models.User(
        name=user.name,
        email=user.email,
        phone=user.phone,
        password=hash_password(user.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Every newly created QuantumPay account gets its own wallet.
    new_wallet = models.Wallet(
        user_id=new_user.id,
        balance=25000.0,
    )

    db.add(new_wallet)
    db.commit()

    return new_user


# =========================================================
# LOGIN USER
# =========================================================

@app.post("/login", response_model=schemas.LoginResponse)
def login_user(
    user: schemas.LoginRequest,
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(models.User)
        .filter(models.User.email == user.email)
        .first()
    )

    if existing_user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not verify_password(
        user.password,
        existing_user.password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    payment_credential = (
        db.query(models.PaymentCredential)
        .filter(
            models.PaymentCredential.user_id
            == existing_user.id
        )
        .first()
    )

    passkey_credential = (
        db.query(passkey_models.PasskeyCredential)
        .filter(
            passkey_models.PasskeyCredential.user_id
            == existing_user.id
        )
        .first()
    )

    return {
        "message": "Login successful",
        "user_id": existing_user.id,
        "name": existing_user.name,
        "email": existing_user.email,
        "payment_pin_set":
            payment_credential is not None,
        "passkey_set":
            passkey_credential is not None,
    }
# =========================================================
# PAYMENT PIN SETUP
# =========================================================

@app.post("/payment-pin/setup")
def setup_payment_pin(
    request: schemas.PaymentPinSetupRequest,
    db: Session = Depends(get_db),
):
    user = (
        db.query(models.User)
        .filter(models.User.id == request.user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if not verify_password(
        request.login_password,
        user.password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid login password",
        )

    passkey_credential = (
        db.query(passkey_models.PasskeyCredential)
        .filter(
            passkey_models.PasskeyCredential.user_id == user.id
        )
        .first()
    )

    if passkey_credential is None:
        raise HTTPException(
            status_code=403,
            detail="Create a passkey before setting the Payment PIN",
        )

    existing = (
        db.query(models.PaymentCredential)
        .filter(
            models.PaymentCredential.user_id == user.id
        )
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Payment PIN already set",
        )

    credential = models.PaymentCredential(
        user_id=user.id,
        pin_hash=hash_password(request.payment_pin),
    )

    db.add(credential)
    db.commit()

    return {
        "message": "Payment PIN created successfully",
        "user_id": user.id,
    }


# =========================================================
# PAYMENT PIN VERIFY
# =========================================================

@app.post("/payment-pin/verify")
def verify_payment_pin_endpoint(
    request: schemas.PaymentPinVerifyRequest,
    db: Session = Depends(get_db),
):
    credential = (
        db.query(models.PaymentCredential)
        .filter(
            models.PaymentCredential.user_id == request.user_id
        )
        .first()
    )

    if credential is None:
        raise HTTPException(
            status_code=404,
            detail="Payment PIN not set",
        )

    if not verify_password(
        request.payment_pin,
        credential.pin_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect Payment PIN",
        )

    return {
        "message": "Payment PIN verified",
        "user_id": request.user_id,
    }


# =========================================================
# VIEW BALANCE WITH PAYMENT PIN
# =========================================================

@app.post("/wallet/balance")
def get_balance_with_pin(
    request: schemas.BalanceRequest,
    db: Session = Depends(get_db),
):
    credential = (
        db.query(models.PaymentCredential)
        .filter(
            models.PaymentCredential.user_id == request.user_id
        )
        .first()
    )

    if credential is None:
        raise HTTPException(
            status_code=403,
            detail="Payment PIN not set",
        )

    if not verify_password(
        request.payment_pin,
        credential.pin_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect Payment PIN",
        )

    wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.user_id == request.user_id)
        .first()
    )

    if wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Wallet not found",
        )

    return {
        "user_id": request.user_id,
        "balance": wallet.balance,
    }


# =========================================================
# PASSKEY REGISTRATION OPTIONS
# =========================================================

@app.post("/passkey/register/options")
def passkey_register_options(
    request: passkey_schemas.PasskeyRegistrationOptionsRequest,
    db: Session = Depends(get_db),
):
    user = (
        db.query(models.User)
        .filter(models.User.id == request.user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if not verify_password(
        request.password,
        user.password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid password",
        )

    challenge = secrets.token_bytes(32)

    registration_options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=f"quantumpay-user-{user.id}".encode("utf-8"),
        user_name=user.email,
        user_display_name=user.name,
        challenge=challenge,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )

    challenge_record = passkey_models.PasskeyChallenge(
        user_id=user.id,
        challenge=registration_options.challenge,
        purpose="REGISTRATION",
        expires_at=datetime.utcnow() + timedelta(minutes=5),
    )

    db.add(challenge_record)
    db.commit()
    db.refresh(challenge_record)

    return {
        "state_id": challenge_record.id,
        "user_id": user.id,
        "options": options_to_json(registration_options),
    }


# =========================================================
# PASSKEY REGISTRATION VERIFICATION
# =========================================================

@app.post("/passkey/register/verify")
def passkey_register_verify(
    request: passkey_schemas.PasskeyRegistrationVerifyRequest,
    db: Session = Depends(get_db),
):
    challenge_record = (
        db.query(passkey_models.PasskeyChallenge)
        .filter(
            passkey_models.PasskeyChallenge.id == request.state_id
        )
        .first()
    )

    if challenge_record is None:
        raise HTTPException(
            status_code=404,
            detail="Registration state not found",
        )

    if challenge_record.purpose != "REGISTRATION":
        raise HTTPException(
            status_code=400,
            detail="Invalid registration state",
        )

    if datetime.utcnow() > challenge_record.expires_at:
        db.delete(challenge_record)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Registration challenge expired",
        )

    user = (
        db.query(models.User)
        .filter(models.User.id == challenge_record.user_id)
        .first()
    )

    if user is None:
        db.delete(challenge_record)
        db.commit()
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    try:
        verification = verify_registration_response(
            credential=request.credential,
            expected_challenge=challenge_record.challenge,
            expected_origin=RP_ORIGINS,
            expected_rp_id=RP_ID,
            require_user_verification=True,
        )
    except Exception as exc:
        db.delete(challenge_record)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Passkey verification failed: {exc}",
        )

    existing_credential = (
        db.query(passkey_models.PasskeyCredential)
        .filter(
            passkey_models.PasskeyCredential.credential_id
            == verification.credential_id
        )
        .first()
    )

    if existing_credential is not None:
        db.delete(challenge_record)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Passkey is already registered",
        )

    credential = passkey_models.PasskeyCredential(
        user_id=user.id,
        credential_id=verification.credential_id,
        credential_public_key=verification.credential_public_key,
        sign_count=verification.sign_count,
    )

    db.add(credential)
    db.delete(challenge_record)
    db.commit()

    return {
        "message": "Passkey registered successfully",
        "user_id": user.id,
        "credential_id": verification.credential_id.hex(),
        "sign_count": verification.sign_count,
    }


# =========================================================
# PASSKEY LOGIN OPTIONS
# =========================================================

@app.post("/passkey/login/options")
def passkey_login_options(
    request: PasskeyAuthenticationOptionsRequest,
    db: Session = Depends(get_db),
):
    user = (
        db.query(models.User)
        .filter(models.User.email == request.email)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    credentials = (
        db.query(passkey_models.PasskeyCredential)
        .filter(
            passkey_models.PasskeyCredential.user_id == user.id
        )
        .all()
    )

    if not credentials:
        raise HTTPException(
            status_code=404,
            detail="No passkey registered for this account",
        )

    challenge = secrets.token_bytes(32)

    # IMPORTANT: no allow_credentials here. Android can therefore
    # discover a resident/discoverable passkey using the RP ID.
    authentication_options = generate_authentication_options(
        rp_id=RP_ID,
        challenge=challenge,
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    challenge_record = passkey_models.PasskeyChallenge(
        user_id=user.id,
        challenge=authentication_options.challenge,
        purpose="AUTHENTICATION",
        expires_at=datetime.utcnow() + timedelta(minutes=5),
    )

    db.add(challenge_record)
    db.commit()
    db.refresh(challenge_record)

    return {
        "state_id": challenge_record.id,
        "user_id": user.id,
        "email": user.email,
        "options": options_to_json(authentication_options),
    }


# =========================================================
# PASSKEY LOGIN VERIFICATION
# =========================================================

@app.post("/passkey/login/verify")
def passkey_login_verify(
    request: PasskeyAuthenticationVerifyRequest,
    db: Session = Depends(get_db),
):
    challenge_record = (
        db.query(passkey_models.PasskeyChallenge)
        .filter(
            passkey_models.PasskeyChallenge.id == request.state_id
        )
        .first()
    )

    if challenge_record is None:
        raise HTTPException(
            status_code=404,
            detail="Authentication state not found",
        )

    if challenge_record.purpose != "AUTHENTICATION":
        raise HTTPException(
            status_code=400,
            detail="Invalid authentication state",
        )

    if datetime.utcnow() > challenge_record.expires_at:
        db.delete(challenge_record)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Authentication challenge expired",
        )

    try:
        credential_id_text = (
            request.credential.get("rawId")
            or request.credential.get("id")
        )

        if not credential_id_text:
            raise ValueError("Missing credential ID")

        credential_id = base64url_to_bytes(credential_id_text)
    except Exception as exc:
        db.delete(challenge_record)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Invalid passkey credential ID: {exc}",
        )

    credential_record = (
        db.query(passkey_models.PasskeyCredential)
        .filter(
            passkey_models.PasskeyCredential.user_id
            == challenge_record.user_id
        )
        .filter(
            passkey_models.PasskeyCredential.credential_id
            == credential_id
        )
        .first()
    )

    if credential_record is None:
        db.delete(challenge_record)
        db.commit()
        raise HTTPException(
            status_code=401,
            detail="Passkey is not registered for this account",
        )

    try:
        verification = verify_authentication_response(
            credential=request.credential,
            expected_challenge=challenge_record.challenge,
            expected_origin=RP_ORIGINS,
            expected_rp_id=RP_ID,
            credential_public_key=credential_record.credential_public_key,
            credential_current_sign_count=credential_record.sign_count,
            require_user_verification=True,
        )
    except Exception as exc:
        db.delete(challenge_record)
        db.commit()
        raise HTTPException(
            status_code=401,
            detail=f"Passkey authentication failed: {exc}",
        )

    user = (
        db.query(models.User)
        .filter(models.User.id == challenge_record.user_id)
        .first()
    )

    if user is None:
        db.delete(challenge_record)
        db.commit()
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    credential_record.sign_count = verification.new_sign_count
    db.delete(challenge_record)
    db.commit()

    payment_credential = (
        db.query(models.PaymentCredential)
        .filter(models.PaymentCredential.user_id == user.id)
        .first()
    )

    return {
        "message": "Passkey login successful",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "payment_pin_set": payment_credential is not None,
        "sign_count": verification.new_sign_count,
    }


# =========================================================
# WALLET METADATA
# =========================================================

@app.get("/wallet/{user_id}")
def get_wallet_locked(
    user_id: int,
    db: Session = Depends(get_db),
):
    wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.user_id == user_id)
        .first()
    )

    if wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Wallet not found",
        )

    # Do not return the actual balance through this endpoint.
    # The balance is only returned by POST /wallet/balance after PIN verification.
    return {
        "user_id": user_id,
        "balance_locked": True,
    }


# =========================================================
# SEND MONEY WITH PAYMENT PIN
# =========================================================

@app.post("/wallet/send")
def send_money(
    request: schemas.SendMoneyRequest,
    db: Session = Depends(get_db),
):
    # =========================================================
    # 1. FIND SENDER
    # =========================================================

    sender = (
        db.query(models.User)
        .filter(models.User.id == request.sender_id)
        .first()
    )

    if sender is None:
        raise HTTPException(
            status_code=404,
            detail="Sender not found",
        )

    # =========================================================
    # 2. VERIFY PAYMENT PIN
    # =========================================================

    credential = (
        db.query(models.PaymentCredential)
        .filter(
            models.PaymentCredential.user_id == sender.id
        )
        .first()
    )

    if credential is None:
        raise HTTPException(
            status_code=403,
            detail="Payment PIN not set",
        )

    if not verify_password(
        request.payment_pin,
        credential.pin_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect Payment PIN",
        )

    # =========================================================
    # 3. VALIDATE AMOUNT
    # =========================================================

    if request.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be greater than zero",
        )

    # =========================================================
    # 4. FIND SENDER WALLET
    # =========================================================

    sender_wallet = (
        db.query(models.Wallet)
        .filter(
            models.Wallet.user_id == sender.id
        )
        .first()
    )

    if sender_wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Sender wallet not found",
        )

    # =========================================================
    # 5. CHECK SENDER BALANCE
    # =========================================================

    if sender_wallet.balance < request.amount:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance",
        )

    # =========================================================
    # 6. FIND RECEIVER
    #     Existing design supports EMAIL OR PHONE
    # =========================================================

    receiver = (
        db.query(models.User)
        .filter(
            (models.User.email == request.receiver)
            | (models.User.phone == request.receiver)
        )
        .first()
    )

    if receiver is None:
        raise HTTPException(
            status_code=404,
            detail="Receiver not found",
        )

    # =========================================================
    # 7. PREVENT SELF TRANSFER
    # =========================================================

    if receiver.id == sender.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot send money to yourself",
        )

    # =========================================================
    # 8. FIND RECEIVER WALLET
    # =========================================================

    receiver_wallet = (
        db.query(models.Wallet)
        .filter(
            models.Wallet.user_id == receiver.id
        )
        .first()
    )

    if receiver_wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Receiver wallet not found",
        )

    # =========================================================
    # 9. TRANSFER MONEY
    # =========================================================

    sender_wallet.balance -= request.amount
    receiver_wallet.balance += request.amount

    # =========================================================
    # 10. CREATE TRANSACTION
    # =========================================================

    transaction = models.Transaction(
        sender=sender.email,
        receiver=receiver.email,
        amount=request.amount,
        transaction_type="SEND",
    )

    db.add(transaction)

    # ---------------------------------------------------------
    # IMPORTANT:
    # Flush first so SQLite/SQLAlchemy generates transaction.id
    # and timestamp before we calculate the hash.
    # ---------------------------------------------------------

    db.flush()
    db.refresh(transaction)

    # =========================================================
    # 11. CREATE SHA3-256 INTEGRITY HASH
    # =========================================================

    hash_value = transaction_hash(
        transaction_id=transaction.id,
        sender=transaction.sender,
        receiver=transaction.receiver,
        amount=transaction.amount,
        transaction_type=transaction.transaction_type,
        timestamp=transaction.timestamp.isoformat(),
    )

    # =========================================================
    # 12. STORE SHA3-256 INTEGRITY HASH
    # =========================================================

    integrity_record = models.TransactionIntegrity(
        transaction_id=transaction.id,
        integrity_hash=hash_value,
    )

    db.add(integrity_record)

    # =========================================================
    # 13. CREATE ML-DSA-65 DIGITAL SIGNATURE
    #
    # The ML-DSA-65 signature is created over the SHA3-256
    # transaction hash. The private key is never stored in SQLite.
    # =========================================================

    public_key, private_key = get_or_create_keys()

    signature = sign_data(
        hash_value.encode("utf-8"),
        private_key,
    )

    # =========================================================
    # 14. STORE ML-DSA-65 SIGNATURE
    #
    # Public key and signature are Base64 encoded so they can be
    # stored safely as text in SQLite.
    # =========================================================

    signature_record = models.TransactionSignature(
        transaction_id=transaction.id,
        public_key=base64.b64encode(public_key).decode("ascii"),
        signature=base64.b64encode(signature).decode("ascii"),
    )

    db.add(signature_record)

    # =========================================================
    # 15. COMMIT EVERYTHING
    # =========================================================

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(transaction)

    # =========================================================
    # 16. FORMAT TIMESTAMP FOR RESPONSE
    # =========================================================

    transaction_timestamp = transaction.timestamp

    if transaction_timestamp.tzinfo is None:
        transaction_timestamp = transaction_timestamp.replace(
            tzinfo=timezone.utc
        )

    # =========================================================
    # 17. RESPONSE
    # =========================================================

    return {
        "message": "Money sent successfully",
        "sender": sender.email,
        "receiver": receiver.email,
        "amount": request.amount,
        "sender_balance": sender_wallet.balance,
        "transaction_id": transaction.id,
        "timestamp": transaction_timestamp.isoformat(),
        "integrity_hash": hash_value,
        "ml_dsa_signature": base64.b64encode(signature).decode("ascii"),
        "ml_dsa_signature_length": len(signature),
    }
@app.get("/transaction/{transaction_id}/integrity")
def verify_transaction_integrity(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    # =========================================================
    # 1. FIND TRANSACTION
    # =========================================================

    transaction = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.id == transaction_id
        )
        .first()
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    # =========================================================
    # 2. FIND STORED INTEGRITY HASH
    # =========================================================

    integrity_record = (
        db.query(models.TransactionIntegrity)
        .filter(
            models.TransactionIntegrity.transaction_id
            == transaction_id
        )
        .first()
    )

    if integrity_record is None:
        raise HTTPException(
            status_code=404,
            detail="Integrity record not found",
        )

    # =========================================================
    # 3. RECALCULATE SHA3-256
    # =========================================================

    recalculated_hash = transaction_hash(
        transaction_id=transaction.id,
        sender=transaction.sender,
        receiver=transaction.receiver,
        amount=transaction.amount,
        transaction_type=transaction.transaction_type,
        timestamp=transaction.timestamp.isoformat(),
    )

    # =========================================================
    # 4. COMPARE HASHES
    # =========================================================

    is_valid = compare_digest(
        integrity_record.integrity_hash,
        recalculated_hash,
    )

    # =========================================================
    # 5. RETURN RESULT
    # =========================================================

    return {
        "transaction_id": transaction.id,
        "stored_hash": integrity_record.integrity_hash,
        "recalculated_hash": recalculated_hash,
        "integrity_valid": is_valid,
    }

# =========================================================
# TRANSACTION ML-DSA-65 SIGNATURE VERIFICATION
# =========================================================

@app.get("/transaction/{transaction_id}/signature")
def verify_transaction_signature(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    # =========================================================
    # 1. FIND TRANSACTION
    # =========================================================

    transaction = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.id == transaction_id
        )
        .first()
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    # =========================================================
    # 2. FIND STORED SHA3-256 HASH
    # =========================================================

    integrity_record = (
        db.query(models.TransactionIntegrity)
        .filter(
            models.TransactionIntegrity.transaction_id
            == transaction_id
        )
        .first()
    )

    if integrity_record is None:
        raise HTTPException(
            status_code=404,
            detail="Integrity record not found",
        )

    # =========================================================
    # 3. FIND STORED ML-DSA-65 SIGNATURE
    # =========================================================

    signature_record = (
        db.query(models.TransactionSignature)
        .filter(
            models.TransactionSignature.transaction_id
            == transaction_id
        )
        .first()
    )

    if signature_record is None:
        raise HTTPException(
            status_code=404,
            detail="ML-DSA signature record not found",
        )

    # =========================================================
    # 4. RECALCULATE SHA3-256 HASH
    # =========================================================

    recalculated_hash = transaction_hash(
        transaction_id=transaction.id,
        sender=transaction.sender,
        receiver=transaction.receiver,
        amount=transaction.amount,
        transaction_type=transaction.transaction_type,
        timestamp=transaction.timestamp.isoformat(),
    )

    # =========================================================
    # 5. DECODE STORED ML-DSA-65 DATA
    # =========================================================

    try:
        public_key = base64.b64decode(
            signature_record.public_key
        )

        signature = base64.b64decode(
            signature_record.signature
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Stored ML-DSA data is invalid: {exc}",
        )

    # =========================================================
    # 6. VERIFY ML-DSA-65 SIGNATURE
    # =========================================================

    signature_valid = verify_signature(
        recalculated_hash.encode("utf-8"),
        signature,
        public_key,
    )

    # =========================================================
    # 7. RETURN VERIFICATION RESULT
    # =========================================================

    return {
        "transaction_id": transaction.id,
        "stored_hash": integrity_record.integrity_hash,
        "recalculated_hash": recalculated_hash,
        "integrity_valid": compare_digest(
            integrity_record.integrity_hash,
            recalculated_hash,
        ),
        "ml_dsa_signature_valid": signature_valid,
        "signature_algorithm": "ML-DSA-65",
        "signature_length": len(signature),
    }


# =========================================================
# RECEIVE MONEY - DISABLED
# =========================================================

@app.post("/wallet/receive")
def receive_money_disabled():
    raise HTTPException(
        status_code=410,
        detail=(
            "External/fake Receive Money is disabled. "
            "Funds can only enter a wallet through a transfer from another QuantumPay user."
        ),
    )


# =========================================================
# TRANSACTION HISTORY
# =========================================================

@app.get(
    "/transactions/{user_id}",
    response_model=list[schemas.TransactionResponse],
)
def get_transactions(
    user_id: int,
    db: Session = Depends(get_db),
):
    user = (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    transactions = (
        db.query(models.Transaction)
        .filter(
            (models.Transaction.sender == user.email)
            | (models.Transaction.receiver == user.email)
        )
        .order_by(models.Transaction.timestamp.desc())
        .all()
    )

    response = []
    for transaction in transactions:
        timestamp = transaction.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        response.append({
            "id": transaction.id,
            "sender": transaction.sender,
            "receiver": transaction.receiver,
            "amount": transaction.amount,
            "transaction_type": transaction.transaction_type,
            "timestamp": timestamp,
        })

    return response
