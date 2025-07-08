from flask import Blueprint,  jsonify,render_template, request, redirect, url_for, session, flash
from datetime import datetime
import json

from ..models import db, Vemp, Profcv

prof_bp = Blueprint('prof', __name__)

from functools import wraps

def login_required(view):
  @wraps(view)
  def wrapped_view(**kwargs):
    if 'vcpid' not in session:
      flash("Please log in to access this page.", 'info')
      return redirect(url_for('auth.login'))
    return view(**kwargs)
  return wrapped_view

@prof_bp.route('/profiles')
@login_required
def profiles():
    """Displays the profile management."""

    pageaction = request.args.get('pageaction', 'view_prof')
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
    print(intro_card_data_in_db)

    try:
        icard_dict = json.loads(intro_card_data_in_db)
    except (json.JSONDecodeError, TypeError):
        flash("Profile data is corrupted or not valid JSON.", "danger")
        icard_dict = {"error": "profile is currepted"}
        #return redirect(url_for('prof.profiles', pageaction='error'))

    # You may need to define or update pf_view, pf_data, preview_profile as per your logic
    preview_profile = None
    pf_data = icard_dict

    return render_template(
        'profiles.html',
        pageaction=pageaction,
        user_name=user.fullname,
        user_profiles=user_profiles,
        icard_dict=icard_dict)



@prof_bp.route('/save_prof', methods=['POST'])
@login_required
def save_prof():
    section = request.args.get('section')
    user_id = session.get('user_id')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        # Get profile
        profile = Profcv.query.filter_by(user_id=user_id, pf_typ='icard').first()
        if not profile:
            msg = "Profile not found."
            if is_ajax:
                return jsonify({'status': 'error', 'message': msg}), 404
            flash(msg, "danger")
            return redirect(url_for('prof.profiles', pageaction='edit_prof'))

        # Load or initialize data
        try:
            data = json.loads(profile.pf_data) if profile.pf_data else {}
        except json.JSONDecodeError:
            data = {}

        # Update based on section
        if section == 'basic':
            data.update({
                'name': request.form.get('pf_name', ''),
                'email': request.form.get('pf_email', ''),
                'mobile': request.form.get('pf_mobile', ''),
                'telephone': request.form.get('pf_telephone', ''),
                'role': request.form.get('pf_title', ''),
                'organization': request.form.get('pf_company', ''),
                'website': request.form.get('pf_website', '')
            })

        elif section == 'skills':
            skills = request.form.getlist('skills[]')
            data['skills'] = [s.strip() for s in skills if s.strip()]

        elif section == 'services':
            services = request.form.getlist('services[]')
            data['services'] = [s.strip() for s in services if s.strip()]

        else:
            msg = "Invalid section provided."
            if is_ajax:
                return jsonify({'status': 'error', 'message': msg}), 400
            flash(msg, "danger")
            return redirect(url_for('prof.profiles', pageaction='edit_prof'))

        # Save to DB
        profile.pf_data = json.dumps(data, indent=2)
        profile.updated_at = datetime.now()
        db.session.commit()

        msg = f"{section.capitalize()} saved successfully."
        if is_ajax:
            return jsonify({'status': 'success', 'message': msg})
        flash(msg, "success")

    except Exception as e:
        db.session.rollback()
        err_msg = f"Error saving {section}: {str(e)}"
        if is_ajax:
            return jsonify({'status': 'error', 'message': err_msg}), 500
        flash(err_msg, "danger")

    return redirect(url_for('prof.profiles', pageaction='edit_prof'))



