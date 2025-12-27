from __future__ import annotations

import secrets
from werkzeug.utils import secure_filename


def make_token() -> str:
    return secrets.token_urlsafe(32)[:64]


def sanitize_filename(name: str) -> str:
    return secure_filename(name or "cv.pdf")


def allowed_pdf(filename: str, mimetype: str | None) -> bool:
    fn = (filename or "").lower()
    if not fn.endswith(".pdf"):
        return False
    if mimetype and mimetype.lower() not in ("application/pdf", "application/x-pdf"):
        # Many browsers send application/pdf; allow x-pdf too.
        return False
    return True
