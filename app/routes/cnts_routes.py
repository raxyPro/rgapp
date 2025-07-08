# task_routes.py
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, session
from datetime import datetime, date
from ..models import db, Vemp, ChatTopic, ChatTopicUser, ChatMessage

from sqlalchemy.orm import joinedload #i have to learn more about joinedload


cnts_bp = Blueprint('cnts', __name__)

from functools import wraps
def login_required(view):
  @wraps(view)
  def wrapped_view(**kwargs):
    if 'vcpid' not in session:
      flash("Please log in to access this page.", 'info')
      return redirect(url_for('auth.login'))
    return view(**kwargs)
  return wrapped_view


@cnts_bp.route('/cntshome', methods=['GET', 'POST'])
@login_required
def cntshome():
    from sqlalchemy import select
    import json

    # Step 1: Get all active employees
    active_users = (
        db.session.query(Vemp.ID, Vemp.vcpid, Vemp.fullname, Vemp.email)
        .filter(Vemp.status == 'Active')
        .all()
    )

    # Step 2: Join with profcv to get public_name, public_title, location
    profcv_data = db.session.execute(
        """
        SELECT vcpid, pf_data
        FROM profcv
        WHERE status = 'Active'
        """
    ).fetchall()

    # Step 3: Build a lookup dictionary from profcv
    profcv_lookup = {}
    for vcpid, pf_data in profcv_data:
        try:
            data = json.loads(pf_data)
            profcv_lookup[vcpid] = {
                "public_name": data.get("public_name", ""),
                "public_title": data.get("public_title", ""),
                "location": data.get("location", "Not specified")
            }
        except Exception as e:
            profcv_lookup[vcpid] = {
                "public_name": "",
                "public_title": "",
                "location": "Not specified"
            }

    # Step 4: Merge with Vemp data
    contacts = []
    for user in active_users:
        vcpid = user.vcpid
        profile = profcv_lookup.get(vcpid, {})
        contacts.append({
            "id": user.ID,
            "vcpid": vcpid,
            "fullname": user.fullname,
            "email": user.email,
            "public_name": profile.get("public_name", user.fullname),
            "public_title": profile.get("public_title", ""),
            "location": profile.get("location", "")
        })

    return render_template("cnts_home.html", contacts=contacts)
