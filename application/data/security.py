import hashlib
import secrets
import hmac


def _pbkdf2(password: str, salt: bytes, iterations: int = 200000):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def hash_password(password: str, iterations: int = 200000):
    salt = secrets.token_bytes(16)
    digest = _pbkdf2(password, salt, iterations)
    return digest.hex(), salt.hex(), iterations


def verify_password(password: str, salt_hex: str, iterations: int, hash_hex: str):
    salt = bytes.fromhex(salt_hex)
    calc = _pbkdf2(password, salt, iterations).hex()
    return hmac.compare_digest(calc, hash_hex)
