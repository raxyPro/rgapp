from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from .models import db, Vemp, Profcv

bp_prof = Blueprint('prof', __name__)

from functools import wraps

def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'user_code' not in session:
            flash("Please log in to access this page.", 'info')
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view

@bp_prof.route('/profiles')
@login_required
def profiles():
    """Displays the profile management."""

    pageaction = request.args.get('pageaction', 'view')
    user_code = session.get('user_code')
    user_id = session.get('user_id')
    print(f"User Code: {user_code}, User ID: {user_id}")
    user = Vemp.query.filter_by(code=user_code).first()
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('auth.logout'))

    user_profiles = Profcv.query.filter_by(user_id=user_id, pf_typ='icard').order_by(Profcv.id.asc()).all()
    if not user_profiles:
        # Create default profiles if none exist
        today = datetime.now()
        default_profiles = [
            Profcv(user_id=user_id, pf_typ='icard', pf_name='Intro Card', pf_data='{}', created_at=today, updated_at=today),
        ]
        db.session.add_all(default_profiles)
        db.session.commit()
        user_profiles = Profcv.query.filter_by(user_id=user_id, pf_typ='icard').order_by(Profcv.id.asc()).all()
    
    import json

    intro_card_data_in_db = user_profiles[0].pf_data

    try:
        icard_dict = json.loads(intro_card_data_in_db)
    except (json.JSONDecodeError, TypeError):
        flash("Profile data is corrupted or not valid JSON.", "danger")
        return redirect(url_for('prof.profiles'))

    # You may need to define or update pf_view, pf_data, preview_profile as per your logic
    preview_profile = None
    pf_data = intro_card_data_in_db

    return render_template(
        'profiles.html',
        pageaction=pageaction
        user_name=user.fullname,
        pf_data=pf_data,
        user_profiles=user_profiles,
        icard_dict=icard_dict)

@bp_prof.route('/save_prof', methods=['GET', 'POST'])
@login_required
def save_prof():
    if request.method == 'POST':
        prof_id = 1  # request.form.get('id')
        xml_data = request.form.get('xmlData')
        print(xml_data)
        if not prof_id or not xml_data:
            flash("Missing profile ID or data.", "danger")
            return redirect(url_for('prof.profiles'))

        profile = Profcv.query.filter_by(id=prof_id, user_id=session.get('user_id')).first()
        if not profile:
            flash("Profile not found.", "danger")
            return redirect(url_for('prof.profiles'))

        profile.pf_data = xml_data
        profile.updated_at = datetime.now()
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for('prof.profiles'))

    return redirect(url_for('prof.profiles'))
