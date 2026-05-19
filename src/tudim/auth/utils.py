import hashlib


def hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()
