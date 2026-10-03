from pathlib import Path
import base64

from ml_dsa_security import generate_keys


BASE_DIR = Path(__file__).resolve().parent

PRIVATE_KEY_FILE = BASE_DIR / "ml_dsa_private.key"
PUBLIC_KEY_FILE = BASE_DIR / "ml_dsa_public.key"


def get_or_create_keys():
    """
    Load the existing ML-DSA-65 key pair.
    If the keys do not exist, generate them once and save them.
    """

    if PRIVATE_KEY_FILE.exists() and PUBLIC_KEY_FILE.exists():

        private_key = base64.b64decode(
            PRIVATE_KEY_FILE.read_text()
        )

        public_key = base64.b64decode(
            PUBLIC_KEY_FILE.read_text()
        )

        return public_key, private_key

    public_key, private_key = generate_keys()

    PRIVATE_KEY_FILE.write_text(
        base64.b64encode(private_key).decode("ascii")
    )

    PUBLIC_KEY_FILE.write_text(
        base64.b64encode(public_key).decode("ascii")
    )

    return public_key, private_key