from pathlib import Path

import secrets

from hmac import compare_digest

from datetime import datetime, timedelta, timezone

from security import hash_password, verify_password

from hash_utils import transaction_hash

import base64
from security_message_service import SecurityMessageService


from ml_dsa_security import sign_data, verify_signature

from ml_dsa_keys import get_or_create_keys

from fastapi import Depends, FastAPI, HTTPException

from fastapi.responses import FileResponse

from pydantic import BaseModel

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
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
import security_evidence
from security_evidence_service import SecurityEvidenceService

import passkey_models

import passkey_schemas

import schemas

from risk_engine import RiskEngine

from challenge_engine import ChallengeEngine
from message_analyzer import MessageAnalyzer





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



class ExternalPendingTransaction(Base):
    """Pending challenge state for an unregistered receiver identifier."""
    __tablename__ = "external_pending_transactions"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    receiver_identifier = Column(String(150), nullable=False)
    amount = Column(Float, nullable=False)
    risk_score = Column(Integer, nullable=False, default=0)
    risk_reasons = Column(String(2000), nullable=True)
    challenge_result = Column(String(20), nullable=True)
    final_action = Column(String(50), nullable=True)
    status = Column(String(30), nullable=False, default="CHALLENGE_PENDING")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


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



# =========================================================

# BUILD INITIAL RISK DECISION

# =========================================================



def has_previous_successful_transaction(db: Session, sender, receiver) -> bool:
    if receiver is None:
        return False
    existing = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.sender == sender.email,
            models.Transaction.receiver == receiver.email,
            models.Transaction.transaction_type == "SEND",
        )
        .first()
    )
    return existing is not None


def evaluate_initial_risk(
    db: Session,
    sender: models.User,
    receiver=None,
    receiver_identifier: str | None = None,
    risk_context: schemas.RiskContext | None = None,
):
    context = risk_context or schemas.RiskContext()

    # TRUSTED RECEIVER MUST BE CHECKED FIRST.
    trusted_receiver = has_previous_successful_transaction(db, sender, receiver)
    if trusted_receiver:
        result = RiskEngine.assess(
            new_receiver=False,
            suspicious_message=False,
            suspicious_payment_identifier=False,
            location_changed=False,
            network_changed=False,
            new_device=False,
            failed_authentication_attempts=0,
            previous_suspicious_activity=False,
            receiver_reports=False,
            unusual_payment_instruction=False,
        )
        result.risk_level = "LOW"
        result.risk_score = 0
        result.reasons = ["Receiver has previous successful transaction history"]
        return result, True, False

    identifiers = []
    if receiver is not None:
        identifiers.extend([receiver.email, receiver.phone])
    if receiver_identifier:
        identifiers.append(receiver_identifier)

    suspicious_identifier = False
    evidence_reasons = []
    seen = set()
    for identifier in identifiers:
        if not identifier or identifier in seen:
            continue
        seen.add(identifier)
        evidence = SecurityEvidenceService.check_identifier(db=db, identifier=identifier)
        if evidence["is_suspicious"]:
            suspicious_identifier = True
            evidence_reasons.extend(evidence["reasons"])

    result = RiskEngine.assess(
        new_receiver=True,
        suspicious_message=context.suspicious_message,
        suspicious_payment_identifier=(context.suspicious_payment_identifier or suspicious_identifier),
        location_changed=context.location_changed,
        network_changed=context.network_changed,
        new_device=context.new_device,
        failed_authentication_attempts=context.failed_authentication_attempts,
        previous_suspicious_activity=context.previous_suspicious_activity,
        receiver_reports=context.receiver_reports,
        unusual_payment_instruction=context.unusual_payment_instruction,
    )

    if receiver is None:
        result.reasons.insert(0, "Receiver is not registered in QuantumPay")
    else:
        result.reasons.insert(0, "Receiver has no previous trusted transaction history")
    if evidence_reasons:
        result.reasons.extend(evidence_reasons)

    # Every untrusted/new receiver enters Challenge Engine.
    result.risk_level = "HIGH"
    return result, False, True


# =========================================================

# ADAPTIVE WALLET SEND

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

    # 2. VALIDATE AMOUNT

    # =========================================================



    if request.amount <= 0:

        raise HTTPException(

            status_code=400,

            detail="Amount must be greater than zero",

        )



    # =========================================================

    # 3. FIND RECEIVER

    #     Supports EMAIL OR PHONE

    # =========================================================



    receiver = (

        db.query(models.User)

        .filter(

            (models.User.email == request.receiver)

            | (models.User.phone == request.receiver)

        )

        .first()

    )



    # IMPORTANT: an unregistered receiver is NOT rejected here.
    # It must enter the Risk Engine and Challenge Engine.

    # =========================================================

    # 4. PREVENT SELF TRANSFER

    # =========================================================



    if receiver is not None and receiver.id == sender.id:

        raise HTTPException(

            status_code=400,

            detail="You cannot send money to yourself",

        )



    # =========================================================

    # 5. FIND SENDER WALLET

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

    # 6. CHECK BALANCE

    # =========================================================



    if sender_wallet.balance < request.amount:

        raise HTTPException(

            status_code=400,

            detail="Insufficient balance",

        )



    # =========================================================

    # 7. RECEIVER WALLET
    # =========================================================

    receiver_wallet = None
    if receiver is not None:
        receiver_wallet = (
            db.query(models.Wallet)
            .filter(models.Wallet.user_id == receiver.id)
            .first()
        )
        if receiver_wallet is None:
            raise HTTPException(
                status_code=404,
                detail="Receiver wallet not found",
            )

    # =========================================================
    # 8. INITIAL RISK ENGINE
    # Amount is NOT passed to the Risk Engine.
    # request.message is NOT analyzed here.
    # =========================================================

    risk_context = request.risk_context or schemas.RiskContext()

    risk_result, trusted_receiver, challenge_required = evaluate_initial_risk(
        db=db,
        sender=sender,
        receiver=receiver,
        receiver_identifier=request.receiver,
        risk_context=risk_context,
    )

    # =========================================================

    # 9. LOW-RISK FLOW

    #

    # LOW → PIN → SHA3 → TRANSACTION

    #

    # No ML-DSA for LOW.

    # =========================================================



    if risk_result.risk_level == "LOW":



        # -----------------------------------------------------

        # Verify Payment PIN

        # -----------------------------------------------------



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



        # -----------------------------------------------------

        # Transfer money

        # -----------------------------------------------------



        sender_wallet.balance -= request.amount

        receiver_wallet.balance += request.amount



        # -----------------------------------------------------

        # Create transaction

        # -----------------------------------------------------



        transaction = models.Transaction(

            sender=sender.email,

            receiver=receiver.email,

            amount=request.amount,

            transaction_type="SEND",

        )



        db.add(transaction)

        db.flush()

        db.refresh(transaction)



        # -----------------------------------------------------

        # SHA3-256 transaction binding

        # -----------------------------------------------------



        hash_value = transaction_hash(

            transaction_id=transaction.id,

            sender=transaction.sender,

            receiver=transaction.receiver,

            amount=transaction.amount,

            transaction_type=transaction.transaction_type,

            timestamp=transaction.timestamp.isoformat(),

        )



        # -----------------------------------------------------

        # Store SHA3-256 integrity hash

        # -----------------------------------------------------



        integrity_record = models.TransactionIntegrity(

            transaction_id=transaction.id,

            integrity_hash=hash_value,

        )



        db.add(integrity_record)



        # -----------------------------------------------------

        # Store Risk Assessment

        # -----------------------------------------------------



        risk_assessment = models.RiskAssessment(

            transaction_id=transaction.id,

            sender_id=sender.id,

            receiver_id=receiver.id,

            risk_score=risk_result.risk_score,

            initial_risk="LOW",

            risk_reasons="; ".join(risk_result.reasons),

            challenge_result=None,

            final_risk="LOW",

            final_action="AUTHORIZED",

        )



        db.add(risk_assessment)



        # -----------------------------------------------------

        # Commit LOW transaction

        # -----------------------------------------------------



        db.commit()

        db.refresh(transaction)



        return {

            "status": "SUCCESS",

            "initial_risk": "LOW",

            "final_risk": "LOW",

            "risk_score": risk_result.risk_score,

            "reasons": risk_result.reasons,

            "transaction_id": transaction.id,

            "amount": request.amount,

            "ml_dsa_used": False,

            "message": "Low-risk transaction authorized using Payment PIN and SHA3-256.",

        }



    # =========================================================

    # 10. HIGH-RISK FLOW

    #

    # HIGH → CHALLENGE

    #

    # IMPORTANT:

    # NO MONEY IS TRANSFERRED HERE.

    # =========================================================



    if risk_result.risk_level == "HIGH" and receiver is None:

        external_pending = ExternalPendingTransaction(
            sender_id=sender.id,
            receiver_identifier=request.receiver,
            amount=request.amount,
            risk_score=risk_result.risk_score,
            risk_reasons="; ".join(risk_result.reasons),
            final_action="CHALLENGE_REQUIRED",
            status="CHALLENGE_PENDING",
        )
        db.add(external_pending)
        db.commit()
        db.refresh(external_pending)

        questions = ChallengeEngine.get_questions(risk_result.reasons)

        return {
            "status": "CHALLENGE_REQUIRED",
            "initial_risk": "HIGH",
            "risk_score": risk_result.risk_score,
            "reasons": risk_result.reasons,
            "pending_transaction_id": -external_pending.id,
            "receiver_registered": False,
            "questions": questions,
            "message": "Receiver is unregistered. Complete the security challenge before the external payment can continue.",
        }


    if risk_result.risk_level == "HIGH":



        # -----------------------------------------------------

        # Create initial Risk Assessment

        # -----------------------------------------------------



        risk_assessment = models.RiskAssessment(

            transaction_id=None,

            sender_id=sender.id,

            receiver_id=receiver.id,

            risk_score=risk_result.risk_score,

            initial_risk="HIGH",

            risk_reasons="; ".join(risk_result.reasons),

            challenge_result=None,

            final_risk=None,

            final_action="CHALLENGE_REQUIRED",

        )



        db.add(risk_assessment)

        db.flush()



        # -----------------------------------------------------

        # Create pending transaction

        # -----------------------------------------------------



        pending = models.PendingTransaction(

            sender_id=sender.id,

            receiver_id=receiver.id,

            amount=request.amount,

            risk_assessment_id=risk_assessment.id,

            status="CHALLENGE_PENDING",

        )



        db.add(pending)

        db.commit()

        db.refresh(pending)



        # -----------------------------------------------------

        # Get Challenge Engine questions

        # -----------------------------------------------------



        questions = ChallengeEngine.get_questions(

            risk_result.reasons

        )



        return {

            "status": "CHALLENGE_REQUIRED",

            "initial_risk": "HIGH",

            "risk_score": risk_result.risk_score,

            "reasons": risk_result.reasons,

            "pending_transaction_id": pending.id,

            "questions": questions,

            "message": "Additional contextual verification is required.",

        }



    # =========================================================

    # 11. SAFETY FALLBACK

    # =========================================================



    raise HTTPException(

        status_code=400,

        detail="Invalid risk decision",

    )

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





# =========================================================

# RISK ENGINE TEST

# =========================================================



@app.post("/risk/test")

def test_risk_engine(

    request: schemas.RiskContext,

):

    result = RiskEngine.assess(

        suspicious_message=request.suspicious_message,

        suspicious_payment_identifier=request.suspicious_payment_identifier,

        location_changed=request.location_changed,

        network_changed=request.network_changed,

        new_device=request.new_device,

        failed_authentication_attempts=request.failed_authentication_attempts,

        previous_suspicious_activity=request.previous_suspicious_activity,

        receiver_reports=request.receiver_reports,

        unusual_payment_instruction=request.unusual_payment_instruction,

    )



    return {

        "risk_level": result.risk_level,

        "risk_score": result.risk_score,

        "reasons": result.reasons,

    }



# =========================================================

# UNREGISTERED RECEIVER RISK TEST

# =========================================================

@app.post("/risk/test-unregistered")
def test_unregistered_receiver_risk(
    request: schemas.SendMoneyRequest,
    db: Session = Depends(get_db),
):
    sender = db.query(models.User).filter(models.User.id == request.sender_id).first()
    if sender is None:
        raise HTTPException(status_code=404, detail="Sender not found")
    context = request.risk_context or schemas.RiskContext()
    result, _, _ = evaluate_initial_risk(
        db=db, sender=sender, receiver=None, receiver_identifier=request.receiver, risk_context=context
    )
    return {
        "receiver": request.receiver,
        "receiver_registered": False,
        "risk_level": result.risk_level,
        "risk_score": result.risk_score,
        "reasons": result.reasons,
    }


# =========================================================

# CHALLENGE ENGINE - QUESTIONS

# =========================================================



@app.get("/risk/challenge/questions")

def get_challenge_questions():



    questions = ChallengeEngine.get_questions()



    return {

        "questions": questions

    }

# =========================================================

# CHALLENGE ENGINE - ANALYZE ANSWERS

# =========================================================



@app.post("/risk/challenge/analyze")

def analyze_challenge_answers(

    request: schemas.ChallengeAnswersRequest,

):



    result = ChallengeEngine.analyze_answers(

        request.answers

    )



    return {

        "final_risk": result.final_risk,

        "challenge_score": result.challenge_score,

        "reasons": result.reasons,

    }



# =========================================================

# COMPLETE HIGH-RISK TRANSACTION CHALLENGE

# =========================================================

@app.post("/wallet/challenge/complete")
def complete_transaction_challenge(
    request: schemas.ChallengeCompletionRequest,
    db: Session = Depends(get_db),
):
    # -----------------------------------------------------
    # UNREGISTERED RECEIVER CHALLENGE
    # Negative pending IDs refer to ExternalPendingTransaction.
    # -----------------------------------------------------
    if request.pending_transaction_id < 0:
        external_id = abs(request.pending_transaction_id)
        external_pending = (
            db.query(ExternalPendingTransaction)
            .filter(ExternalPendingTransaction.id == external_id)
            .first()
        )
        if external_pending is None:
            raise HTTPException(status_code=404, detail="External pending transaction not found")
        if external_pending.status != "CHALLENGE_PENDING":
            raise HTTPException(status_code=400, detail="This external transaction is no longer pending")

        challenge_result = ChallengeEngine.analyze_answers(request.answers)
        external_pending.challenge_result = challenge_result.final_risk

        if challenge_result.final_risk == "HIGH":
            external_pending.status = "BLOCKED"
            external_pending.final_action = "BLOCKED"
            db.commit()
            return {
                "status": "BLOCKED",
                "initial_risk": "HIGH",
                "final_risk": "HIGH",
                "challenge_score": challenge_result.challenge_score,
                "reasons": challenge_result.reasons,
                "ml_dsa_used": False,
                "receiver_registered": False,
                "message": "Transaction blocked due to high security risk.",
            }

        if challenge_result.final_risk == "MEDIUM":
            sender = db.query(models.User).filter(models.User.id == external_pending.sender_id).first()
            if sender is None:
                raise HTTPException(status_code=404, detail="Sender not found")

            credential = (
                db.query(models.PaymentCredential)
                .filter(models.PaymentCredential.user_id == sender.id)
                .first()
            )
            if credential is None:
                raise HTTPException(status_code=403, detail="Payment PIN not set")
            if not verify_password(request.payment_pin, credential.pin_hash):
                raise HTTPException(status_code=401, detail="Incorrect Payment PIN")

            sender_wallet = (
                db.query(models.Wallet)
                .filter(models.Wallet.user_id == sender.id)
                .first()
            )
            if sender_wallet is None:
                raise HTTPException(status_code=404, detail="Sender wallet not found")
            if sender_wallet.balance < external_pending.amount:
                raise HTTPException(status_code=400, detail="Insufficient wallet balance")

            # External receiver has no QuantumPay wallet. We therefore debit
            # the sender and record the outgoing payment using the identifier.
            sender_wallet.balance -= external_pending.amount

            transaction = models.Transaction(
                sender=sender.email,
                receiver=external_pending.receiver_identifier,
                amount=external_pending.amount,
                transaction_type="SEND",
            )
            db.add(transaction)
            db.flush()
            db.refresh(transaction)

            hash_value = transaction_hash(
                transaction_id=transaction.id,
                sender=transaction.sender,
                receiver=transaction.receiver,
                amount=transaction.amount,
                transaction_type=transaction.transaction_type,
                timestamp=transaction.timestamp.isoformat(),
            )
            db.add(models.TransactionIntegrity(transaction_id=transaction.id, integrity_hash=hash_value))

            public_key, private_key = get_or_create_keys()
            signature = sign_data(hash_value.encode("utf-8"), private_key)
            db.add(models.TransactionSignature(
                transaction_id=transaction.id,
                public_key=base64.b64encode(public_key).decode("utf-8"),
                signature=base64.b64encode(signature).decode("utf-8"),
            ))

            external_pending.status = "COMPLETED"
            external_pending.final_action = "AUTHORIZED"
            db.commit()
            db.refresh(transaction)

            return {
                "status": "SUCCESS",
                "initial_risk": "HIGH",
                "final_risk": "MEDIUM",
                "challenge_score": challenge_result.challenge_score,
                "transaction_id": transaction.id,
                "amount": external_pending.amount,
                "receiver_registered": False,
                "ml_dsa_used": True,
                "message": "External payment authorized using Payment PIN, SHA3-256, and ML-DSA-65.",
            }

        raise HTTPException(status_code=400, detail="Invalid external challenge result")

    # -----------------------------------------------------
    # 1. Find pending transaction
    # -----------------------------------------------------

    pending = (
        db.query(models.PendingTransaction)
        .filter(
            models.PendingTransaction.id == request.pending_transaction_id
        )
        .first()
    )

    if pending is None:
        raise HTTPException(
            status_code=404,
            detail="Pending transaction not found",
        )

    # -----------------------------------------------------
    # 2. Make sure challenge is still pending
    # -----------------------------------------------------

    if pending.status != "CHALLENGE_PENDING":
        raise HTTPException(
            status_code=400,
            detail="This transaction is no longer pending",
        )

    # -----------------------------------------------------
    # 3. Analyze contextual answers
    # -----------------------------------------------------

    challenge_result = ChallengeEngine.analyze_answers(
        request.answers
    )

    # -----------------------------------------------------
    # 4. Find risk assessment
    # -----------------------------------------------------

    risk_assessment = None

    if pending.risk_assessment_id:
        risk_assessment = (
            db.query(models.RiskAssessment)
            .filter(
                models.RiskAssessment.id == pending.risk_assessment_id
            )
            .first()
        )

    # -----------------------------------------------------
    # 5. Store Challenge Engine result
    # -----------------------------------------------------

    if risk_assessment:
        risk_assessment.challenge_result = challenge_result.final_risk
        risk_assessment.final_risk = challenge_result.final_risk

        # Keep the initial risk reasons and append challenge reasons.
        initial_reasons = risk_assessment.risk_reasons or ""
        challenge_reasons = "; ".join(challenge_result.reasons)

        if challenge_reasons:
            risk_assessment.risk_reasons = (
                f"{initial_reasons}; Challenge: {challenge_reasons}"
                if initial_reasons
                else f"Challenge: {challenge_reasons}"
            )

    # -----------------------------------------------------
    # 6. HIGH → BLOCK
    # -----------------------------------------------------

    if challenge_result.final_risk == "HIGH":
        pending.status = "BLOCKED"

        if risk_assessment:
            risk_assessment.final_action = "BLOCKED"

        db.commit()

        return {
            "status": "BLOCKED",
            "initial_risk": "HIGH",
            "final_risk": "HIGH",
            "challenge_score": challenge_result.challenge_score,
            "reasons": challenge_result.reasons,
            "ml_dsa_used": False,
            "message": "Transaction blocked due to high security risk.",
        }

    # -----------------------------------------------------
    # 7. MEDIUM → PIN → SHA3 → ML-DSA-65 → TRANSACTION
    # -----------------------------------------------------

    if challenge_result.final_risk == "MEDIUM":

        # -------------------------------------------------
        # Find sender
        # -------------------------------------------------

        sender = (
            db.query(models.User)
            .filter(models.User.id == pending.sender_id)
            .first()
        )

        if sender is None:
            raise HTTPException(
                status_code=404,
                detail="Sender not found",
            )

        # -------------------------------------------------
        # Verify Payment PIN
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Find wallets
        # -------------------------------------------------

        sender_wallet = (
            db.query(models.Wallet)
            .filter(models.Wallet.user_id == pending.sender_id)
            .first()
        )

        receiver_wallet = (
            db.query(models.Wallet)
            .filter(models.Wallet.user_id == pending.receiver_id)
            .first()
        )

        if sender_wallet is None or receiver_wallet is None:
            raise HTTPException(
                status_code=404,
                detail="Wallet not found",
            )

        # -------------------------------------------------
        # Check balance
        # -------------------------------------------------

        if sender_wallet.balance < pending.amount:
            raise HTTPException(
                status_code=400,
                detail="Insufficient wallet balance",
            )

        # -------------------------------------------------
        # Find receiver
        # -------------------------------------------------

        receiver = (
            db.query(models.User)
            .filter(models.User.id == pending.receiver_id)
            .first()
        )

        if receiver is None:
            raise HTTPException(
                status_code=404,
                detail="Receiver not found",
            )

        # -------------------------------------------------
        # Transfer money
        # -------------------------------------------------

        sender_wallet.balance -= pending.amount
        receiver_wallet.balance += pending.amount

        # -------------------------------------------------
        # Create transaction
        # -------------------------------------------------

        transaction = models.Transaction(
            sender=sender.email,
            receiver=receiver.email,
            amount=pending.amount,
            transaction_type="SEND",
        )

        db.add(transaction)
        db.flush()
        db.refresh(transaction)

        # Link the final transaction to its risk assessment.
        if risk_assessment:
            risk_assessment.transaction_id = transaction.id

        # -------------------------------------------------
        # SHA3-256 transaction binding
        # -------------------------------------------------

        hash_value = transaction_hash(
            transaction_id=transaction.id,
            sender=transaction.sender,
            receiver=transaction.receiver,
            amount=transaction.amount,
            transaction_type=transaction.transaction_type,
            timestamp=transaction.timestamp.isoformat(),
        )

        # -------------------------------------------------
        # Store SHA3-256 integrity hash
        # -------------------------------------------------

        integrity_record = models.TransactionIntegrity(
            transaction_id=transaction.id,
            integrity_hash=hash_value,
        )

        db.add(integrity_record)

        # -------------------------------------------------
        # ML-DSA-65 authorization
        # -------------------------------------------------

        public_key, private_key = get_or_create_keys()

        signature = sign_data(
            hash_value.encode("utf-8"),
            private_key,
        )

        # -------------------------------------------------
        # Store ML-DSA-65 signature
        # -------------------------------------------------

        signature_record = models.TransactionSignature(
            transaction_id=transaction.id,
            public_key=base64.b64encode(public_key).decode("utf-8"),
            signature=base64.b64encode(signature).decode("utf-8"),
        )

        db.add(signature_record)

        # -------------------------------------------------
        # Update risk assessment
        # -------------------------------------------------

        if risk_assessment:
            risk_assessment.final_action = "AUTHORIZED"

        # -------------------------------------------------
        # Complete pending transaction
        # -------------------------------------------------

        pending.status = "COMPLETED"

        db.commit()
        db.refresh(transaction)

        return {
            "status": "SUCCESS",
            "initial_risk": "HIGH",
            "final_risk": "MEDIUM",
            "challenge_score": challenge_result.challenge_score,
            "transaction_id": transaction.id,
            "amount": pending.amount,
            "ml_dsa_used": True,
            "message": "Transaction authorized using Payment PIN, SHA3-256, and ML-DSA-65.",
        }

    # -----------------------------------------------------
    # Safety fallback
    # -----------------------------------------------------

    raise HTTPException(
        status_code=400,
        detail="Invalid challenge result",
    )
