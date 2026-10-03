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

from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey





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




# =========================================================
# SECURITY MESSAGE / RISK NUMBER MODELS
# =========================================================

class IncomingSecurityMessageRequest(BaseModel):
    sender_phone: str
    message_text: str


class RiskNumber(Base):
    """Every phone number involved in a suspicious incoming SMS.

    Both the SMS sender and every phone number extracted from the
    suspicious message are stored. These records are evidence for the
    Risk Engine; they do not permanently label a number as HIGH risk.
    """
    __tablename__ = "risk_numbers"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String(50), nullable=False, index=True)
    identifier_type = Column(String(30), nullable=False, default="PHONE")
    source_type = Column(String(40), nullable=False)
    message_text = Column(String(4000), nullable=False)
    analyzer_score = Column(Integer, nullable=False, default=0)
    analyzer_reasons = Column(String(2000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ExternalPendingTransaction(Base):
    """Pending challenge state for a receiver not registered in QuantumPay."""
    __tablename__ = "external_pending_transactions"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    receiver_identifier = Column(String(150), nullable=False)
    amount = Column(Float, nullable=False)
    risk_score = Column(Integer, nullable=False, default=0)
    risk_reasons = Column(String(4000), nullable=True)
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



def has_previous_successful_transaction(db: Session, sender: models.User, receiver: models.User) -> bool:
    """A previous completed SEND establishes a trusted receiver relationship."""
    row = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.sender == sender.email,
            models.Transaction.receiver == receiver.email,
            models.Transaction.transaction_type == "SEND",
        )
        .first()
    )
    return row is not None


def evaluate_initial_risk(
    db: Session,
    sender: models.User,
    receiver: models.User | None,
    receiver_identifier: str,
    risk_context: schemas.RiskContext | None,
):
    """Evaluate the current transaction using live security evidence.

    Trusted receiver -> LOW immediately.

    New/unregistered + no suspicious evidence -> MEDIUM challenge using
    three questions and SHA3-256 after successful challenge completion.

    New/unregistered + suspicious evidence -> HIGH challenge using six
    questions; a successful challenge reaches MEDIUM and then uses ML-DSA-65.

    Suspicious SMS evidence is a live risk signal, not a permanent HIGH label.
    """
    context = risk_context or schemas.RiskContext()

    trusted_receiver = False
    if receiver is not None:
        trusted_receiver = has_previous_successful_transaction(db, sender, receiver)

    # ---------------------------------------------------------
    # TRUSTED RECEIVER MUST WIN FIRST
    # ---------------------------------------------------------
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
            receiver_reports=0,
            unusual_payment_instruction=False,
        )
        result.risk_level = "LOW"
        result.risk_score = 0
        result.reasons = ["Receiver has previous successful transaction history"]
        return result, True, False, "TRUSTED_LOW"

    # ---------------------------------------------------------
    # LIVE SECURITY EVIDENCE FOR THE CURRENT RECEIVER
    # ---------------------------------------------------------
    # Incoming suspicious SMS creates SecurityEvidence and RiskNumber
    # records. Phone numbers may be entered with spaces or a leading 0,
    # so compare the last 10 digits as the canonical phone identity.
    identifiers = []
    if receiver_identifier:
        identifiers.append(receiver_identifier)
    if receiver is not None:
        identifiers.extend([receiver.email, receiver.phone])

    suspicious_identifier = False
    evidence_reasons = []
    seen = set()

    def phone_key(value):
        if not value:
            return ""
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        return digits[-10:] if len(digits) >= 10 else digits

    # First use the existing SecurityEvidenceService. Try both the exact
    # identifier and its normalized 10-digit phone form.
    for identifier in identifiers:
        if not identifier:
            continue

        candidates = [identifier]
        normalized = phone_key(identifier)
        if normalized and normalized not in candidates:
            candidates.append(normalized)

        for candidate_identifier in candidates:
            if candidate_identifier in seen:
                continue
            seen.add(candidate_identifier)

            evidence = SecurityEvidenceService.check_identifier(
                db=db,
                identifier=candidate_identifier,
            )

            if evidence.get("is_suspicious"):
                suspicious_identifier = True
                evidence_reasons.extend(evidence.get("reasons", []))

    # Also check the RiskNumber records created by the incoming-SMS endpoint.
    # This makes the risk decision use the actual suspicious SMS evidence even
    # when phone formatting differs between the SMS sender and Send Money UI.
    receiver_phone_key = phone_key(receiver_identifier)
    if receiver is not None:
        receiver_phone_key = receiver_phone_key or phone_key(receiver.phone)

    if receiver_phone_key:
        for risk_number in db.query(RiskNumber).all():
            if phone_key(risk_number.identifier) == receiver_phone_key:
                suspicious_identifier = True
                if risk_number.analyzer_reasons:
                    evidence_reasons.append(
                        "Incoming suspicious SMS evidence associated with receiver: "
                        + risk_number.analyzer_reasons
                    )
                else:
                    evidence_reasons.append(
                        "Incoming suspicious SMS evidence associated with receiver"
                    )
                break

    # IMPORTANT:
    # request.message is NOT analyzed here. Only incoming SMS evidence
    # reaches this decision through SecurityEvidenceService/RiskNumber.
    result = RiskEngine.assess(
        new_receiver=True,
        suspicious_message=False,
        suspicious_payment_identifier=suspicious_identifier,
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
        result.reasons.insert(0, "Receiver has no previous successful transaction history")

    if evidence_reasons:
        result.reasons.extend(evidence_reasons)

    # ---------------------------------------------------------
    # CHOOSE THE CHALLENGE CLASS
    # ---------------------------------------------------------
    # IMPORTANT ARCHITECTURE:
    #   Trusted receiver + any suspicious SMS evidence -> LOW.
    #   New/unregistered + NO suspicious receiver evidence -> MEDIUM/CLEAN.
    #   New/unregistered + suspicious receiver evidence -> HIGH/SUSPICIOUS.
    #
    # Do NOT use the aggregate RiskEngine level to select the question set.
    # Otherwise unrelated context signals can incorrectly turn a clean new
    # receiver into the six-question suspicious flow.
    #
    # CLEAN_NEW       -> exactly 3 questions
    # HIGH_SUSPICIOUS -> exactly 6 questions
    # ---------------------------------------------------------
    if suspicious_identifier:
        result.risk_level = "HIGH"
        mode = ChallengeEngine.MODE_HIGH_SUSPICIOUS
    else:
        result.risk_level = "MEDIUM"
        mode = ChallengeEngine.MODE_CLEAN_NEW

    return result, False, True, mode


@app.post("/wallet/send")
def send_money(
    request: schemas.SendMoneyRequest,
    db: Session = Depends(get_db),
):
    # =========================================================
    # 1. FIND SENDER
    # =========================================================
    sender = db.query(models.User).filter(models.User.id == request.sender_id).first()
    if sender is None:
        raise HTTPException(status_code=404, detail="Sender not found")

    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    receiver_identifier = (request.receiver or "").strip()
    if not receiver_identifier:
        raise HTTPException(status_code=400, detail="Receiver is required")

    # =========================================================
    # 2. FIND REGISTERED RECEIVER, IF ANY
    # =========================================================
    # Find a registered receiver by email or phone.
    # Phone comparison also accepts common formatting differences such as
    # spaces and a leading 0 (for example 08680088899 vs 8680088899).
    receiver = (
        db.query(models.User)
        .filter(
            (models.User.email == receiver_identifier)
            | (models.User.phone == receiver_identifier)
        )
        .first()
    )

    if receiver is None:
        receiver_digits = "".join(ch for ch in receiver_identifier if ch.isdigit())
        if len(receiver_digits) >= 10:
            receiver_digits = receiver_digits[-10:]
            for candidate in db.query(models.User).all():
                candidate_digits = "".join(ch for ch in (candidate.phone or "") if ch.isdigit())
                if len(candidate_digits) >= 10 and candidate_digits[-10:] == receiver_digits:
                    receiver = candidate
                    break

    if receiver is not None and receiver.id == sender.id:
        raise HTTPException(status_code=400, detail="You cannot send money to yourself")

    # IMPORTANT: outgoing request.message is NOT analyzed.
    # Only incoming SMS -> MessageAnalyzer -> SecurityEvidenceService
    # can create suspicious evidence for this risk decision.
    risk_context = request.risk_context or schemas.RiskContext()

    risk_result, trusted_receiver, challenge_required, challenge_mode = evaluate_initial_risk(
        db=db,
        sender=sender,
        receiver=receiver,
        receiver_identifier=receiver_identifier,
        risk_context=risk_context,
    )

    # =========================================================
    # 3. TRUSTED RECEIVER -> LOW -> PIN -> SHA3 -> SUCCESS
    # =========================================================
    if trusted_receiver:
        credential = db.query(models.PaymentCredential).filter(
            models.PaymentCredential.user_id == sender.id
        ).first()
        if credential is None:
            raise HTTPException(status_code=403, detail="Payment PIN not set")
        if not verify_password(request.payment_pin, credential.pin_hash):
            raise HTTPException(status_code=401, detail="Incorrect Payment PIN")

        sender_wallet = db.query(models.Wallet).filter(
            models.Wallet.user_id == sender.id
        ).first()
        receiver_wallet = db.query(models.Wallet).filter(
            models.Wallet.user_id == receiver.id
        ).first()

        if sender_wallet is None or receiver_wallet is None:
            raise HTTPException(status_code=404, detail="Wallet not found")
        if sender_wallet.balance < request.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        sender_wallet.balance -= request.amount
        receiver_wallet.balance += request.amount

        transaction = models.Transaction(
            sender=sender.email,
            receiver=receiver.email,
            amount=request.amount,
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
        db.add(models.TransactionIntegrity(
            transaction_id=transaction.id,
            integrity_hash=hash_value,
        ))
        db.add(models.RiskAssessment(
            transaction_id=transaction.id,
            sender_id=sender.id,
            receiver_id=receiver.id,
            risk_score=0,
            initial_risk="LOW",
            risk_reasons="Receiver has previous successful transaction history",
            challenge_result=None,
            final_risk="LOW",
            final_action="AUTHORIZED",
        ))
        db.commit()
        db.refresh(transaction)

        return {
            "status": "SUCCESS",
            "initial_risk": "LOW",
            "final_risk": "LOW",
            "risk_score": 0,
            "reasons": risk_result.reasons,
            "transaction_id": transaction.id,
            "amount": request.amount,
            "ml_dsa_used": False,
            "receiver_registered": True,
            "message": "Low-risk transaction authorized using Payment PIN and SHA3-256.",
        }

    # =========================================================
    # 4. NEW REGISTERED RECEIVER
    # =========================================================
    if receiver is not None:
        initial_risk = "HIGH" if challenge_mode == ChallengeEngine.MODE_HIGH_SUSPICIOUS else "MEDIUM"
        pending_status = (
            "CHALLENGE_PENDING_HIGH"
            if challenge_mode == ChallengeEngine.MODE_HIGH_SUSPICIOUS
            else "CHALLENGE_PENDING_CLEAN"
        )

        risk_assessment = models.RiskAssessment(
            transaction_id=None,
            sender_id=sender.id,
            receiver_id=receiver.id,
            risk_score=risk_result.risk_score,
            initial_risk=initial_risk,
            risk_reasons="; ".join(risk_result.reasons),
            challenge_result=None,
            final_risk=None,
            final_action="CHALLENGE_REQUIRED",
        )
        db.add(risk_assessment)
        db.flush()

        pending = models.PendingTransaction(
            sender_id=sender.id,
            receiver_id=receiver.id,
            amount=request.amount,
            risk_assessment_id=risk_assessment.id,
            status=pending_status,
        )
        db.add(pending)
        db.commit()
        db.refresh(pending)

        questions = ChallengeEngine.get_questions(
            risk_result.reasons,
            mode=challenge_mode,
        )

        return {
            "status": "CHALLENGE_REQUIRED",
            "initial_risk": initial_risk,
            "risk_score": risk_result.risk_score,
            "reasons": risk_result.reasons,
            "pending_transaction_id": pending.id,
            "receiver_registered": True,
            "challenge_mode": challenge_mode,
            "questions": questions,
            "message": (
                "New receiver. Complete the 3-question contextual check."
                if challenge_mode == ChallengeEngine.MODE_CLEAN_NEW
                else "Suspicious receiver evidence detected. Complete the high-risk contextual check."
            ),
        }

    # =========================================================
    # 5. COMPLETELY UNREGISTERED RECEIVER
    # =========================================================
    # No receiver wallet exists. If approved, the sender wallet is debited
    # and the outgoing transaction records the raw receiver identifier.
    initial_risk = "HIGH" if challenge_mode == ChallengeEngine.MODE_HIGH_SUSPICIOUS else "MEDIUM"
    pending_status = (
        "CHALLENGE_PENDING_HIGH"
        if challenge_mode == ChallengeEngine.MODE_HIGH_SUSPICIOUS
        else "CHALLENGE_PENDING_CLEAN"
    )

    external = ExternalPendingTransaction(
        sender_id=sender.id,
        receiver_identifier=receiver_identifier,
        amount=request.amount,
        risk_score=risk_result.risk_score,
        risk_reasons="; ".join(risk_result.reasons),
        status=pending_status,
    )
    db.add(external)
    db.commit()
    db.refresh(external)

    return {
        "status": "CHALLENGE_REQUIRED",
        "initial_risk": initial_risk,
        "risk_score": risk_result.risk_score,
        "reasons": risk_result.reasons,
        "pending_transaction_id": -external.id,
        "receiver_registered": False,
        "challenge_mode": challenge_mode,
        "questions": ChallengeEngine.get_questions(
            risk_result.reasons,
            mode=challenge_mode,
        ),
        "message": (
            "Receiver is not registered. Complete the 3-question contextual check."
            if challenge_mode == ChallengeEngine.MODE_CLEAN_NEW
            else "Suspicious receiver evidence detected. Complete the high-risk contextual check."
        ),
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
# LIVE INCOMING SECURITY SMS
# =========================================================

@app.post("/security/messages/receive")
def receive_security_message(
    request: IncomingSecurityMessageRequest,
    db: Session = Depends(get_db),
):
    try:
        result = SecurityMessageService.receive_message(
            db=db,
            sender_phone=request.sender_phone,
            message_text=request.message_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Store BOTH the suspicious SMS sender and EVERY phone number found
    # inside the suspicious message under risk_numbers.
    if result.get("is_suspicious"):
        numbers=[]
        sender=result.get("sender_phone")
        if sender:
            numbers.append((sender, "SMS_SENDER"))
        for number in result.get("extracted_phone_numbers", []):
            if number and number != sender:
                numbers.append((number, "MESSAGE_NUMBER"))

        for identifier, source_type in numbers:
            db.add(RiskNumber(
                identifier=identifier,
                identifier_type="PHONE",
                source_type=source_type,
                message_text=result.get("message", request.message_text),
                analyzer_score=int(result.get("score", 0)),
                analyzer_reasons="; ".join(result.get("reasons", [])),
            ))
        db.commit()

    return result


@app.get("/risk/numbers")
def get_risk_numbers(db: Session = Depends(get_db)):
    rows=db.query(RiskNumber).order_by(RiskNumber.created_at.desc()).all()
    return {
        "risk_numbers":[{
            "id":r.id, "identifier":r.identifier,
            "identifier_type":r.identifier_type, "source_type":r.source_type,
            "analyzer_score":r.analyzer_score,
            "analyzer_reasons":r.analyzer_reasons,
            "created_at":r.created_at,
        } for r in rows]
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
    """Complete either the clean-new or suspicious-high challenge.

    CLEAN_NEW + safe -> PIN + SHA3-256 -> SUCCESS (no ML-DSA)
    HIGH_SUSPICIOUS + safe -> PIN + SHA3-256 + ML-DSA-65 -> SUCCESS
    Any challenge result HIGH -> BLOCKED
    """

    # =========================================================
    # A. UNREGISTERED RECEIVER
    # =========================================================
    if request.pending_transaction_id < 0:
        external_id = abs(request.pending_transaction_id)
        external = (
            db.query(ExternalPendingTransaction)
            .filter(ExternalPendingTransaction.id == external_id)
            .first()
        )

        if external is None:
            raise HTTPException(
                status_code=404,
                detail="External pending transaction not found",
            )

        if external.status not in {
            "CHALLENGE_PENDING",
            "CHALLENGE_PENDING_CLEAN",
            "CHALLENGE_PENDING_HIGH",
        }:
            raise HTTPException(
                status_code=400,
                detail="This transaction is no longer pending",
            )

        # Old CHALLENGE_PENDING records came from the previous 6-question
        # implementation, so keep them on the high-suspicious path.
        challenge_mode = (
            ChallengeEngine.MODE_CLEAN_NEW
            if external.status == "CHALLENGE_PENDING_CLEAN"
            else ChallengeEngine.MODE_HIGH_SUSPICIOUS
        )
        initial_risk = "MEDIUM" if challenge_mode == ChallengeEngine.MODE_CLEAN_NEW else "HIGH"

        challenge_result = ChallengeEngine.analyze_answers(
            request.answers,
            mode=challenge_mode,
        )
        external.challenge_result = challenge_result.final_risk

        # HIGH result -> block. Never sign a blocked transaction.
        if challenge_result.final_risk == "HIGH":
            external.status = "BLOCKED"
            external.final_action = "BLOCKED"
            db.commit()
            return {
                "status": "BLOCKED",
                "initial_risk": initial_risk,
                "final_risk": "HIGH",
                "challenge_score": challenge_result.challenge_score,
                "reasons": challenge_result.reasons,
                "ml_dsa_used": False,
                "receiver_registered": False,
                "message": "Transaction blocked due to high security risk.",
            }

        # ---------------------------------------------------------
        # MEDIUM RESULT -> PIN
        # ---------------------------------------------------------
        sender = db.query(models.User).filter(
            models.User.id == external.sender_id
        ).first()
        if sender is None:
            raise HTTPException(status_code=404, detail="Sender not found")

        credential = db.query(models.PaymentCredential).filter(
            models.PaymentCredential.user_id == sender.id
        ).first()
        if credential is None:
            raise HTTPException(status_code=403, detail="Payment PIN not set")
        if not verify_password(request.payment_pin, credential.pin_hash):
            raise HTTPException(status_code=401, detail="Incorrect Payment PIN")

        wallet = db.query(models.Wallet).filter(
            models.Wallet.user_id == sender.id
        ).first()
        if wallet is None:
            raise HTTPException(status_code=404, detail="Sender wallet not found")
        if wallet.balance < external.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        wallet.balance -= external.amount

        transaction = models.Transaction(
            sender=sender.email,
            receiver=external.receiver_identifier,
            amount=external.amount,
            transaction_type="SEND",
        )
        db.add(transaction)
        db.flush()
        db.refresh(transaction)

        # SHA3-256 is used for BOTH clean-new and suspicious flows.
        hash_value = transaction_hash(
            transaction_id=transaction.id,
            sender=transaction.sender,
            receiver=transaction.receiver,
            amount=transaction.amount,
            transaction_type=transaction.transaction_type,
            timestamp=transaction.timestamp.isoformat(),
        )
        db.add(models.TransactionIntegrity(
            transaction_id=transaction.id,
            integrity_hash=hash_value,
        ))

        ml_dsa_used = False

        # ML-DSA is used ONLY for the suspicious/high initial flow.
        if challenge_mode == ChallengeEngine.MODE_HIGH_SUSPICIOUS:
            public_key, private_key = get_or_create_keys()
            signature = sign_data(hash_value.encode("utf-8"), private_key)
            db.add(models.TransactionSignature(
                transaction_id=transaction.id,
                public_key=base64.b64encode(public_key).decode("utf-8"),
                signature=base64.b64encode(signature).decode("utf-8"),
            ))
            ml_dsa_used = True

        external.status = "COMPLETED"
        external.final_action = "AUTHORIZED"
        db.commit()
        db.refresh(transaction)

        return {
            "status": "SUCCESS",
            "initial_risk": initial_risk,
            "final_risk": "MEDIUM",
            "challenge_score": challenge_result.challenge_score,
            "transaction_id": transaction.id,
            "amount": external.amount,
            "receiver_registered": False,
            "ml_dsa_used": ml_dsa_used,
            "message": (
                "Unregistered receiver authorized using Payment PIN and SHA3-256."
                if not ml_dsa_used
                else "Unregistered suspicious receiver authorized using Payment PIN, SHA3-256, and ML-DSA-65."
            ),
        }

    # =========================================================
    # B. REGISTERED NEW RECEIVER
    # =========================================================
    pending = (
        db.query(models.PendingTransaction)
        .filter(models.PendingTransaction.id == request.pending_transaction_id)
        .first()
    )

    if pending is None:
        raise HTTPException(status_code=404, detail="Pending transaction not found")

    if pending.status not in {
        "CHALLENGE_PENDING",
        "CHALLENGE_PENDING_CLEAN",
        "CHALLENGE_PENDING_HIGH",
    }:
        raise HTTPException(
            status_code=400,
            detail="This transaction is no longer pending",
        )

    risk_assessment = None
    if pending.risk_assessment_id:
        risk_assessment = (
            db.query(models.RiskAssessment)
            .filter(models.RiskAssessment.id == pending.risk_assessment_id)
            .first()
        )

    # Old CHALLENGE_PENDING records are from the previous high-risk flow.
    if pending.status == "CHALLENGE_PENDING_CLEAN":
        challenge_mode = ChallengeEngine.MODE_CLEAN_NEW
    elif pending.status == "CHALLENGE_PENDING_HIGH":
        challenge_mode = ChallengeEngine.MODE_HIGH_SUSPICIOUS
    elif risk_assessment and risk_assessment.initial_risk == "MEDIUM":
        challenge_mode = ChallengeEngine.MODE_CLEAN_NEW
    else:
        challenge_mode = ChallengeEngine.MODE_HIGH_SUSPICIOUS

    initial_risk = "MEDIUM" if challenge_mode == ChallengeEngine.MODE_CLEAN_NEW else "HIGH"

    challenge_result = ChallengeEngine.analyze_answers(
        request.answers,
        mode=challenge_mode,
    )

    if risk_assessment:
        risk_assessment.challenge_result = challenge_result.final_risk
        risk_assessment.final_risk = challenge_result.final_risk
        initial_reasons = risk_assessment.risk_reasons or ""
        challenge_reasons = "; ".join(challenge_result.reasons)
        if challenge_reasons:
            risk_assessment.risk_reasons = (
                f"{initial_reasons}; Challenge: {challenge_reasons}"
                if initial_reasons
                else f"Challenge: {challenge_reasons}"
            )

    # HIGH result -> BLOCK
    if challenge_result.final_risk == "HIGH":
        pending.status = "BLOCKED"
        if risk_assessment:
            risk_assessment.final_action = "BLOCKED"
        db.commit()
        return {
            "status": "BLOCKED",
            "initial_risk": initial_risk,
            "final_risk": "HIGH",
            "challenge_score": challenge_result.challenge_score,
            "reasons": challenge_result.reasons,
            "ml_dsa_used": False,
            "receiver_registered": True,
            "message": "Transaction blocked due to high security risk.",
        }

    # ---------------------------------------------------------
    # MEDIUM RESULT -> PIN + SHA3
    # ---------------------------------------------------------
    sender = db.query(models.User).filter(
        models.User.id == pending.sender_id
    ).first()
    if sender is None:
        raise HTTPException(status_code=404, detail="Sender not found")

    credential = db.query(models.PaymentCredential).filter(
        models.PaymentCredential.user_id == sender.id
    ).first()
    if credential is None:
        raise HTTPException(status_code=403, detail="Payment PIN not set")
    if not verify_password(request.payment_pin, credential.pin_hash):
        raise HTTPException(status_code=401, detail="Incorrect Payment PIN")

    sender_wallet = db.query(models.Wallet).filter(
        models.Wallet.user_id == pending.sender_id
    ).first()
    receiver_wallet = db.query(models.Wallet).filter(
        models.Wallet.user_id == pending.receiver_id
    ).first()

    if sender_wallet is None or receiver_wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")
    if sender_wallet.balance < pending.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    sender_wallet.balance -= pending.amount
    receiver_wallet.balance += pending.amount

    receiver = db.query(models.User).filter(
        models.User.id == pending.receiver_id
    ).first()
    if receiver is None:
        raise HTTPException(status_code=404, detail="Receiver not found")

    transaction = models.Transaction(
        sender=sender.email,
        receiver=receiver.email,
        amount=pending.amount,
        transaction_type="SEND",
    )
    db.add(transaction)
    db.flush()
    db.refresh(transaction)

    if risk_assessment:
        risk_assessment.transaction_id = transaction.id

    hash_value = transaction_hash(
        transaction_id=transaction.id,
        sender=transaction.sender,
        receiver=transaction.receiver,
        amount=transaction.amount,
        transaction_type=transaction.transaction_type,
        timestamp=transaction.timestamp.isoformat(),
    )
    db.add(models.TransactionIntegrity(
        transaction_id=transaction.id,
        integrity_hash=hash_value,
    ))

    ml_dsa_used = False

    # Suspicious/high initial flow gets the PQ signature after MEDIUM.
    if challenge_mode == ChallengeEngine.MODE_HIGH_SUSPICIOUS:
        public_key, private_key = get_or_create_keys()
        signature = sign_data(hash_value.encode("utf-8"), private_key)
        db.add(models.TransactionSignature(
            transaction_id=transaction.id,
            public_key=base64.b64encode(public_key).decode("utf-8"),
            signature=base64.b64encode(signature).decode("utf-8"),
        ))
        ml_dsa_used = True

    if risk_assessment:
        risk_assessment.final_action = "AUTHORIZED"

    pending.status = "COMPLETED"
    db.commit()
    db.refresh(transaction)

    return {
        "status": "SUCCESS",
        "initial_risk": initial_risk,
        "final_risk": "MEDIUM",
        "challenge_score": challenge_result.challenge_score,
        "transaction_id": transaction.id,
        "amount": pending.amount,
        "receiver_registered": True,
        "ml_dsa_used": ml_dsa_used,
        "message": (
            "New receiver authorized using Payment PIN and SHA3-256."
            if not ml_dsa_used
            else "Suspicious new receiver authorized using Payment PIN, SHA3-256, and ML-DSA-65."
        ),
    }

