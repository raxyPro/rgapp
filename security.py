"""
Central place for password hashing/verification.
Later you can migrate to argon2id or another scheme by changing only this file.
"""

from passlib.hash import bcrypt


def hash_password(plain_password: str) -> str:
    if not plain_password or len(plain_password) < 8:
        raise ValueError("Password must be at least 8 characters")
    return bcrypt.hash(plain_password)


def verify_password(plain_password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    try:
        return bcrypt.verify(plain_password, stored_hash)
    except Exception:
        return False
