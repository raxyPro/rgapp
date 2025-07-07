# auth_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
from ..models import db, Vemp
from datetime import date

auth_bp = Blueprint('auth', __name__)

from functools import wraps
def login_required(view):
  @wraps(view)
  def wrapped_view(**kwargs):
    if 'user_code' not in session:
      flash("Please log in to access this page.", 'info')
      return redirect(url_for('auth.login'))
    return view(**kwargs)
  return wrapped_view

# --- Index ---
@auth_bp.route('/')
def index():
    """Redirects to dashboard if logged in, otherwise to login page."""
    print("hi")
    print("Session variables:", dict(session))
    if 'user_code' in session:
        return redirect(url_for('auth.start'))
    return redirect(url_for('auth.login'))

# --- Sample Transaction Route ---


@auth_bp.route('/start')
def start():
    """Redirects to dashboard if logged in, otherwise to login page."""
    print("hi")
    print("Session variables:", dict(session))
    if 'user_code' in session:
        #return redirect(url_for('prof.profiles'))
        return redirect(url_for('auth.dashboard'))

    return redirect(url_for('auth.login'))

# --- Dashboard ---
@auth_bp.route('/dashboard')
@login_required
def dashboard():    
    # Fetch tasks for the current user
    from ..models import TaskManager  # Import here to avoid circular import
    from ..models import ChatManager  # Chatmanager 
    user_id=session.get('user_id')
    tm = TaskManager(db.session)
    user_tasks = tm.get_tasks_by_user(user_id)
    #user_chats=ChatManager._get_chat_by_user(user_id)
    cm  = ChatManager(db.session)
    user_chats = cm.get_chats_by_user(user_id)
    print(user_tasks,user_chats)
    return render_template('dashboard.html', tasks=user_tasks,chats=user_chats)

# --- Login ---
@auth_bp.route('/login', methods=('GET', 'POST'))
def login():
    if 'user_code' in session:
        return redirect(url_for('auth.start'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        pin = request.form.get('pin', '').strip()
        error = None

        user = Vemp.query.filter_by(email=email).first()

        if not user or not user.pin_hash or not check_password_hash(user.pin_hash, pin):
            error = "Incorrect email or PIN."

        if error is None:
            session.clear()
            session.permanent = True
            session['user_id'] = user.user_id
            session['user_code'] = user.code
            session['user_email'] = user.email
            session['user_name'] = user.fullname 
            session['user_role'] = user.user_role
            print("hi",user.user_role)
            #flash(f"Welcome back, {user.fullname or user.email}!", 'success')
            return redirect(url_for('auth.dashboard'))
        else:
            flash(error, 'danger')

    return render_template('login.html')


# --- Logout ---
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", 'info')
    return redirect(url_for('auth.login'))

# --- Forgot PIN ---
@auth_bp.route('/forgot_pin', methods=('GET', 'POST'))
def forgot_pin():
    if request.method == 'POST':
        email = request.form['email'].strip()
        user = Vemp.query.filter_by(email=email).first()

        if user:
            reset_token = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(hours=1)
            user.reset_token = reset_token
            user.reset_token_expires_at = expires_at
            db.session.commit()

            reset_link = url_for('auth.set_pin', token=reset_token, _external=True)
            print(f"\n--- PIN Reset Link (SIMULATED EMAIL) ---\n"
                  f"To: {email}\n"
                  f"Click to reset your PIN: {reset_link}\n")

            flash("A PIN reset link has been sent to your email (check console for link).", 'success')
            return render_template('message.html', message="PIN reset link sent!")
        else:
            flash("No account found with that email.", 'danger')

    return render_template('forgot_pin.html')


# --- Set PIN ---
@auth_bp.route('/set_pin/<token>', methods=('GET', 'POST'))
def set_pin(token):
    user = Vemp.query.filter_by(reset_token=token).first()

    if not user:
        flash("Invalid or expired PIN reset link.", 'danger')
        return redirect(url_for('auth.login'))

    if user.reset_token_expires_at and datetime.now() > user.reset_token_expires_at:
        user.reset_token = None
        user.reset_token_expires_at = None
        db.session.commit()
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
            user.pin_hash = generate_password_hash(new_pin)
            user.reset_token = None
            user.reset_token_expires_at = None
            db.session.commit()
            flash("Your PIN has been successfully set. You can now log in.", 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(error, 'danger')

    return render_template('set_pin.html', token=token)
