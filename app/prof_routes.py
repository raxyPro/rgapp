# auth_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
from .models import db, Vemp,Profcv
from datetime import date

prof_bp = Blueprint('prof', __name__)

from functools import wraps
import os
from flask import current_app
def login_required(view):
  @wraps(view)
  def wrapped_view(**kwargs):
    if 'user_code' not in session:
      flash("Please log in to access this page.", 'info')
      return redirect(url_for('auth.login'))
    return view(**kwargs)
  return wrapped_view



@prof_bp.route('/profiles')
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
            Profcv(user_id=user_id, pf_typ='icard', pf_name='Intro Card', pf_data='', created_at=today, updated_at=today),
            #Profcv(user_id=user_id, pf_typ='cvp1', pf_name='Summary CV', pf_data='', created_at=today, updated_at=today),
            #Profcv(user_id=user_id, pf_typ='cvp2', pf_name='Detail CV', pf_data='', created_at=today, updated_at=today),
        ]
        db.session.add_all(default_profiles)
        db.session.commit()
        user_profiles = Profcv.query.filter_by(user_id=user_id, pf_typ='icard').order_by(Profcv.id.asc()).all()
    
    # Example: Parse the pf_data XML of the first profile (if exists)
    import xml.etree.ElementTree as ET
    preview_profile=False 
    icard_data = None
    pf_data=user_profiles[0].pf_data
    if user_profiles and user_profiles[0].pf_data:
        try:
            icard_data = ET.fromstring(user_profiles[0].pf_data)
            icard_dict = {child.tag: child.text for child in icard_data}
            # Extract Services as a list from icard_data XML
            services_elem = icard_data.find('Services')
            services_list = []
            if services_elem is not None:
                for service in services_elem.findall('Service'):
                    services_list.append(service.text)
            icard_dict['Services'] = services_list
            preview_profile=True
        except Exception as e:
            icard_data = None
            flash("No Preview - Could not parse profile XML data.", "warning")
    print(icard_data)
    return render_template(
        'profiles.html',
        user_name=user.fullname,
        pf_view=preview_profile,
        pf_data=pf_data,
        icard_dict=icard_dict if preview_profile else None,
        pageaction=pageaction,
        user_profiles=user_profiles,
        user_code=user_code,
        user_id=user_id
    )

@prof_bp.route('/save_prof', methods=['GET', 'POST'])
@login_required
def save_prof():
    if request.method == 'POST':
        prof_id = 1 #request.form.get('id')
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
    pass

