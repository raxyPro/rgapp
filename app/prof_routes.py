# auth_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
from .models import db, Vemp,Profcv
from datetime import date

prof_bp = Blueprint('prof', __name__)


# --- Profiles ---
@prof_bp.route('/profiles')
def profiles():
    """Displays the profile management."""
    user_code = session.get('user_code')
    user_id = session.get('user_id')
    print(f"User Code: {user_code}, User ID: {user_id}")
    user = Vemp.query.filter_by(code=user_code).first()
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('auth.logout'))

    user_profiles = Profcv.query.filter_by(user_id=user_id).order_by(Profcv.id.asc()).all()
    print(f"User Profiles: {user_profiles}")
    return render_template('profiles.html', user_name=user.fullname or user.email, Profs=user_profiles)

