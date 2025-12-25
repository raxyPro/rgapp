from itsdangerous import URLSafeTimedSerializer
from flask import current_app

def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="rb-invite")

def generate_invite_token(email: str) -> str:
    return _serializer().dumps({"email": email})

def verify_invite_token(token: str, max_age_seconds: int = 60 * 60 * 24 * 7):  # 7 days
    s = _serializer()
    return s.loads(token, max_age=max_age_seconds)  # returns dict with email
