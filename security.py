"""Autenticação simples por papel, sem credenciais no código ou na URL."""
import hashlib
import hmac
import os

ITERATIONS = 400_000


def hash_password(password: str, salt: bytes | None = None) -> str:
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError('Use uma senha com pelo menos 12 caracteres.')
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        kind, iterations, salt_hex, digest_hex = encoded.split('$')
        if kind != 'pbkdf2_sha256':
            return False
        rounds = int(iterations)
        if not (200_000 <= rounds <= 2_000_000):
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                     bytes.fromhex(salt_hex), rounds)
        return hmac.compare_digest(actual, bytes.fromhex(digest_hex))
    except (ValueError, TypeError, AttributeError):
        return False


def safe_user_entry(text):
    """Impede fórmulas introduzidas por campos livres no Google Sheets."""
    value = str(text or '').replace('\x00', '')
    if value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value
