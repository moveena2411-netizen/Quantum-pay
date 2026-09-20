from pydantic import BaseModel


# =========================================================
# PASSKEY REGISTRATION OPTIONS REQUEST
# =========================================================

class PasskeyRegistrationOptionsRequest(BaseModel):
    user_id: int
    password: str


# =========================================================
# PASSKEY REGISTRATION VERIFY REQUEST
# =========================================================

class PasskeyRegistrationVerifyRequest(BaseModel):
    state_id: int
    credential: dict


# =========================================================
# PASSKEY AUTHENTICATION OPTIONS REQUEST
# =========================================================

class PasskeyAuthenticationOptionsRequest(BaseModel):
    email: str


# =========================================================
# PASSKEY AUTHENTICATION VERIFY REQUEST
# =========================================================

class PasskeyAuthenticationVerifyRequest(BaseModel):
    state_id: int
    credential: dict