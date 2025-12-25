from flask import Blueprint, redirect, url_for
from flask_login import current_user

home_bp = Blueprint("home", __name__)

@home_bp.route("/")
def index():
    if current_user.is_authenticated:
        u = current_user.get_user()
        return redirect(url_for("admin.dashboard" if u.is_admin else "user.welcome"))
    return redirect(url_for("auth.login"))
