import base64
import hashlib
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from environs import Env
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator


AES_GCM_PREFIX = 'v2:'
AES_GCM_NONCE_SIZE = 12


def _get_secret_key() -> str | None:
    Env().read_env()
    return (
        os.getenv('SECRET_KEY_AUTH')
        or os.getenv('TOKEN_AUTH_SECRET_KEY')
        or os.getenv('DODO_TOKEN_AUTH_SECRET_KEY')
    )


def decrypt_account_name(value: str | None) -> str | None:
    if value is None or not value.startswith(AES_GCM_PREFIX):
        return value

    secret_key = _get_secret_key()
    if not secret_key:
        return value

    payload = value.removeprefix(AES_GCM_PREFIX)
    raw = base64.urlsafe_b64decode(payload.encode())
    nonce = raw[:AES_GCM_NONCE_SIZE]
    encrypted = raw[AES_GCM_NONCE_SIZE:]

    try:
        return AESGCM(hashlib.sha256(secret_key.encode()).digest()).decrypt(
            nonce,
            encrypted,
            None,
        ).decode()
    except (InvalidTag, ValueError):
        return value


class EncryptedAccountName(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_result_value(self, value, dialect):
        return decrypt_account_name(value)
