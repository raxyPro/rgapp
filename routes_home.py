from flask import Blueprint, redirect, url_for
from flask_login import current_user
from extensions import db
from models import RBUserModule, RBModule

home_bp = Blueprint("home", __name__)

@home_bp.route("/")
def index():
    if current_user.is_authenticated:
        u = current_user.get_user()
        if u.is_admin:
            return redirect(url_for("admin.dashboard"))

        return redirect(url_for("user.welcome"))
    return redirect(url_for("auth.login"))
