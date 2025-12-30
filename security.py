"""
Central place for password hashing/verification.
Later you can migrate to argon2id or another scheme by changing only this file.
"""

from passlib.hash import bcrypt




def hash_password(plain_password: str) -> str:
    if plain_password is None:
        raise ValueError("Password missing")

    # common prod issues: whitespace/newlines
    plain_password = plain_password.strip()

    b = plain_password.encode("utf-8")
    if len(b) > 72:
        raise ValueError(
            f"Password too long for bcrypt: {len(b)} bytes (max 72). "
            "Fix env/pepper override or switch to argon2."
        )

    return bcrypt.hash(plain_password)



def verify_password(plain_password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    try:
        return bcrypt.verify(plain_password, stored_hash)
    except Exception:
        return False
