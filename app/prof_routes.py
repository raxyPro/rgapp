# auth_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
from models import db, Vemp
from datetime import date

prof_bp = Blueprint('prof', __name__)


# --- Profiles ---
@prof_bp.route('/profiles')
def profiles():
    """Displays the profile management."""
    user_code = session.get('user_code')
    user = Vemp.query.filter_by(code=user_code).first()
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('auth.logout'))

    # Fetch tasks for the current user
    from models import Task  # Import here to avoid circular import

    user_tasks = Task.query.filter_by(user_code=user_code).order_by(Task.due_date.asc()).all()
    for t in user_tasks:
        if t.due_date:
            days_left = (t.due_date - date.today()).days
            t.due_soon = (0 <= days_left <= 3) and t.status != 'Completed'
        else:
            t.due_soon = False

    return render_template('profiles.html', user_name=user.fullname or user.email, tasks=user_tasks)

