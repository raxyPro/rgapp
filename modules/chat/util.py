# modules/chat/util.py
# Keep this module lightweight and dependency-safe for imports in blueprints.
try:
    from flask_login import current_user
except Exception:  # pragma: no cover - fallback for environments where flask_login is missing
    current_user = None  # type: ignore

def get_current_user_id() -> int:
    """
    Works with RBUser directly OR adapter objects (like UserLoginAdapter).
    Tries common patterns:
      - current_user.user_id
      - current_user.id
      - current_user.user.user_id
      - current_user.get_id()
    """
    if current_user is None:
        raise AttributeError("Cannot determine logged-in user id: flask_login.current_user unavailable")

    # RBUser style
    if hasattr(current_user, "user_id"):
        return int(getattr(current_user, "user_id"))

    # Flask-Login common
    if hasattr(current_user, "id"):
        return int(getattr(current_user, "id"))

    # Adapter wrapping a real user object
    if hasattr(current_user, "user"):
        u = getattr(current_user, "user")
        if hasattr(u, "user_id"):
            return int(getattr(u, "user_id"))
        if hasattr(u, "id"):
            return int(getattr(u, "id"))

    # Flask-Login required API
    if hasattr(current_user, "get_id"):
        return int(current_user.get_id())

    raise AttributeError("Cannot determine logged-in user id from current_user")

__all__ = ["get_current_user_id"]
