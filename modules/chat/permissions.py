# modules/chat/permissions.py
from __future__ import annotations

from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user

from extensions import db
from models import RBUserModule, RBModule

from modules.chat.models import ChatThreadMember


def _real_user():
    """Return the underlying RBUser object whether current_user is RBUser or an adapter."""
    u = current_user
    if hasattr(u, "get_user"):
        try:
            u = u.get_user()
        except Exception:
            pass
    return u


def module_required(module_key: str):
    """Enforce module access using rb_user_module.

    Rules:
    - Must be logged in
    - Admin users always pass
    - Otherwise, user must have an rb_user_module row for module_key with has_access = 1
    """

    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not getattr(current_user, "is_authenticated", False):
                abort(401)

            u = _real_user()
            if not u or not getattr(u, "user_id", None):
                flash("Unable to verify user. Please sign in again.", "warning")
                return redirect(url_for("user.welcome"))

            if getattr(u, "is_admin", False):
                return fn(*args, **kwargs)

            has = (
                db.session.query(RBUserModule)
                .join(RBModule, RBModule.module_key == RBUserModule.module_key)
                .filter(
                    RBUserModule.user_id == u.user_id,
                    RBUserModule.module_key == module_key,
                    RBUserModule.has_access.is_(True),
                    RBModule.is_enabled.is_(True),
                )
                .first()
            )
            if not has:
                mod = db.session.query(RBModule).filter(RBModule.module_key == module_key).first()
                mod_name = mod.name if mod and getattr(mod, "name", None) else module_key.upper()
                flash(f"You do not have access to the {mod_name} module.", "warning")
                return redirect(url_for("user.welcome"))

            return fn(*args, **kwargs)

        return wrapper

    return deco


def require_thread_member(thread_id: int, user_id: int):
    """Abort 403 if user_id is not a member of the thread."""
    m = ChatThreadMember.query.filter_by(thread_id=thread_id, user_id=user_id).first()
    if not m:
        abort(403)
