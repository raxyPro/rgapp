# auth_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
from .models import db, Vemp,Profcv
from datetime import date

prof_bp = Blueprint('prof', __name__)

from functools import wraps
def login_required(view):
  @wraps(view)
  def wrapped_view(**kwargs):
    if 'user_code' not in session:
      flash("Please log in to access this page.", 'info')
      return redirect(url_for('auth.login'))
    return view(**kwargs)
  return wrapped_view



# --- Profiles ---
@prof_bp.route('/profiles')
@login_required
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
    for t in user_profiles:
        print(t.id,t.pf_typ, t.pf_name)
    print(f"User Profiles: {user_profiles}")
    return render_template('profiles.html', user_name=user.fullname or user.email, Profs=user_profiles)

@prof_bp.route('/add_prof', methods=['GET', 'POST'])
@login_required
def add_prof():
    """Adds a new profile."""
    if request.method == 'POST':
        pf_typ = request.form.get('pf_typ')
        pf_name = request.form.get('pf_name')
        pf_data = request.form.get('pf_data')
        user_id = session.get('user_id')
        print(f"Adding profile for User ID: {user_id}, Type: {pf_typ}, Name: {pf_name}")
        if not pf_typ or not pf_name or not pf_data:
            flash(f"All fields are required.{user_id} {pf_typ} {pf_name} {pf_data}", "danger")
            return redirect(url_for('prof.add_prof'))

        new_profile = Profcv(
            user_id=user_id,
            pf_typ=pf_typ,
            pf_name=pf_name,
            pf_data=pf_data,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.session.add(new_profile)
        db.session.commit()
        flash("Profile added successfully.", "success")
        return redirect(url_for('prof.profiles'))

    return render_template('add_edit_prof.html', PageAction="Add Profile", cv_data="")



@prof_bp.route('/edit_prof/<int:prof_id>', methods=['GET', 'POST'])
@login_required
def edit_prof(prof_id):
    """Edits an existing profile."""
    user_id = session.get('user_id')
    profile = Profcv.query.filter_by(id=prof_id, user_id=user_id).first()
    if not profile:
        flash("Profile not found or access denied.", "danger")
        return redirect(url_for('prof.profiles'))

    if request.method == 'POST':
        pf_typ = request.form.get('pf_typ')
        pf_name = request.form.get('pf_name')
        pf_data = request.form.get('pf_data')
        if not pf_typ or not pf_name or not pf_data:
            flash("All fields are required.", "danger")
            return redirect(url_for('prof.edit_prof', prof_id=prof_id))

        profile.pf_typ = pf_typ
        profile.pf_name = pf_name
        profile.pf_data = pf_data
        profile.updated_at = datetime.now()
        # No need to add profile to session again; just commit
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for('prof.profiles'))
    return render_template('add_edit_prof.html', PageAction="Edit Profile", profile=profile, cv_data=profile.pf_data)