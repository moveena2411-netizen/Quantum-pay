from pqcrypto.sign.ml_dsa_65 import (
    keygen,
    sign,
    verify,
)


def generate_keys():
    """
    Generate an ML-DSA-65 public/private key pair.
    """
    public_key, private_key = keygen()

    return public_key, private_key


def sign_data(data: bytes, private_key: bytes) -> bytes:
    """
    Create an ML-DSA-65 digital signature.
    """
    return sign(
        private_key,
        data,
    )


def verify_signature(
    data: bytes,
    signature: bytes,
    public_key: bytes,
) -> bool:
    """
    Verify an ML-DSA-65 digital signature.
    """
    try:
        verify(
            public_key,
            data,
            signature,
        )

        return True

    except Exception:
        return False