from itsdangerous import URLSafeTimedSerializer
from flask import current_app

def _serializer(salt: str):
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=salt)

# ---- Invite tokens ----
def generate_invite_token(email: str) -> str:
    return _serializer("rb-invite").dumps({"email": email})

def verify_invite_token(token: str, max_age_seconds: int = 60 * 60 * 24 * 7):
    return _serializer("rb-invite").loads(token, max_age=max_age_seconds)

# ---- Password reset tokens ----
def generate_reset_token(email: str) -> str:
    return _serializer("rb-reset").dumps({"email": email})

def verify_reset_token(token: str, max_age_seconds: int = 60 * 30):  # 30 minutes
    return _serializer("rb-reset").loads(token, max_age=max_age_seconds)
