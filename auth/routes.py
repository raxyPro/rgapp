# my_flask_app/auth/routes.py
from flask import render_template, request, redirect, url_for, session, g, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid # For reset tokens

from . import auth_bp
from .. import db # Import db from the main app package
from ..models import User # Import User model to interact with MySQL User table


# Access the login_required decorator from the application's globals
# We need to get it after app context is available
def get_login_required():
    return current_app.jinja_env.globals.get('login_required')

# Helper to get the MS Access DB connection
def get_access_db():
    return current_app.extensions['flask_sqlalchemy'].db # Get the SQLAlchemy db instance, then use get_access_db_conn helper
    # No, this is incorrect. We need the g.access_db_conn directly from the __init__.py function.
    # It's better to pass it in directly or make get_access_db_conn part of a global access pattern.
    # For now, let's assume g.access_db_conn is available if the decorator runs.
    # A cleaner way would be to make get_access_db_conn callable from here.
    # Let's adjust __init__.py to make it accessible via app.get_access_db_conn
    
    # Re-reading __init__.py, get_access_db_conn is already defined.
    # We just need to call it from here.
    return g.access_db_conn if 'access_db_conn' in g else None # Direct access via g

@auth_bp.route('/login', methods=('GET', 'POST'))
def login():
    if 'user_id' in session:
        # Redirect to the tasks blueprint dashboard
        return redirect(url_for('tasks.dashboard'))

    if request.method == 'POST':
        email = request.form['email'].strip()
        pin = request.form['pin'].strip()
        error = None

        conn = get_access_db() # Get the MS Access DB connection
        if conn is None: # Handle connection failure
            flash("Could not connect to the authentication database.", 'danger')
            return render_template('login.html')

        user_record = conn.execute(
            'SELECT code, email, pin_hash, fullname FROM vemp WHERE email = ?', (email,)
        ).fetchone()

        if user_record is None:
            error = "Incorrect email or PIN."
        # Use user_record[2] for pin_hash as per your original code
        elif not check_password_hash(user_record[2], pin):
            error = "Incorrect email or PIN."

        if error is None:
            session.clear()
            session['user_id'] = user_record[0] # MS Access 'code'
            session['user_email'] = user_record[1]
            session['user_fullname'] = user_record[3] # Store full name
            session.permanent = True
            flash(f"Welcome back, {user_record[3]}!", 'success')
            return redirect(url_for('tasks.dashboard')) # Redirect to tasks blueprint dashboard
        else:
            flash(error, 'danger')

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot_pin', methods=('GET', 'POST'))
def forgot_pin():
    if request.method == 'POST':
        email = request.form['email'].strip()
        conn = get_access_db()
        if conn is None:
            flash("Could not connect to the authentication database.", 'danger')
            return render_template('forgot_pin.html')

        # Note: 'id' in your original query for 'vemp' was 'code'.
        # Assuming `code` is the PK of vemp and user[0] corresponds to it.
        user_record = conn.execute(
            'SELECT code, email FROM vemp WHERE email = ?', (email,)
        ).fetchone()

        if user_record:
            reset_token = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(hours=1)

            # Update vemp table in MS Access
            conn.execute(
                'UPDATE vemp SET reset_token = ?, reset_token_expires_at = ? WHERE code = ?',
                (reset_token, expires_at, user_record[0])
            )
            conn.commit()

            reset_link = url_for('auth.set_pin', token=reset_token, _external=True)
            current_app.logger.info(f"\n--- PIN Reset Link (SIMULATED EMAIL) ---\n"
                                     f"To: {email}\n"
                                     f"Subject: Your PIN Reset Request\n"
                                     f"Click the link to set your new PIN: {reset_link}\n"
                                     f"----------------------------------------\n")
            flash("A PIN reset link has been sent to your email (check console for link).", 'success')
            return render_template('message.html', message="PIN reset link sent!")
        else:
            flash("No account found with that email.", 'danger')

    return render_template('forgot_pin.html')

@auth_bp.route('/set_pin/<token>', methods=('GET', 'POST'))
def set_pin(token):
    conn = get_access_db()
    if conn is None:
        flash("Could not connect to the authentication database.", 'danger')
        return redirect(url_for('auth.login'))

    user_record = conn.execute(
        'SELECT code, email, reset_token_expires_at FROM vemp WHERE reset_token = ?', (token,)
    ).fetchone()

    if not user_record:
        flash("Invalid or expired PIN reset link.", 'danger')
        return redirect(url_for('auth.login'))

    expires_at = user_record[2]
    # Handle datetime parsing for MS Access
    if isinstance(expires_at, str):
        try:
            # Try typical Access datetime format (e.g., "YYYY-MM-DD HH:MM:SS" or "MM/DD/YYYY HH:MM:SS AM/PM")
            # You might need to adjust this format string based on your exact Access column output
            expires_at = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                expires_at = datetime.strptime(expires_at, "%m/%d/%Y %I:%M:%S %p")
            except ValueError:
                current_app.logger.error(f"Could not parse datetime string from Access: {user_record[2]}")
                flash("Error parsing expiration date. Please try again.", 'danger')
                return redirect(url_for('auth.login'))

    if datetime.now() > expires_at:
        conn.execute(
            'UPDATE vemp SET reset_token = NULL, reset_token_expires_at = NULL WHERE code = ?',
            (user_record[0],)
        )
        conn.commit()
        flash("Your PIN reset link has expired. Please request a new one.", 'danger')
        return redirect(url_for('auth.forgot_pin'))

    if request.method == 'POST':
        new_pin = request.form['new_pin'].strip()
        confirm_pin = request.form['confirm_pin'].strip()
        error = None

        if len(new_pin) != 4 or not new_pin.isdigit():
            error = "PIN must be a 4-digit number."
        elif new_pin != confirm_pin:
            error = "PINs do not match."

        if error is None:
            hashed_pin = generate_password_hash(new_pin)
            conn.execute(
                'UPDATE vemp SET pin_hash = ?, reset_token = NULL, reset_token_expires_at = NULL WHERE code = ?',
                (hashed_pin, user_record[0])
            )
            conn.commit()
            flash("Your PIN has been successfully set. You can now log in.", 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(error, 'danger')

    return render_template('set_pin.html', token=token)