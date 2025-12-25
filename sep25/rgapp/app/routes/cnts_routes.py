# task_routes.py
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, session
from datetime import datetime, date
from ..models import db, Vemp, Profcv, ChatTopic, ChatTopicUser, ChatMessage

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

    current_vcpid = session.get('vcpid')

    # Step 1: All active users
    active_users = (
        db.session.query(Vemp.ID, Vemp.vcpid, Vemp.fullname, Vemp.email)
        .filter(Vemp.status == 'Active')
        .all()
    )

    # Step 2: Profcv data
    profcv_data = Profcv.query.filter_by(status='Active').with_entities(Profcv.vcpid, Profcv.pf_data).all()
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

    # Step 3: Load all topic memberships of current user
    my_topics = (
        db.session.query(ChatTopicUser.topic_id)
        .filter(ChatTopicUser.vcpid == current_vcpid)
        .all()
    )
    my_topic_ids = {t[0] for t in my_topics}

    # Step 4: Load all topic-user mappings for those topics
    topic_user_map = (
        db.session.query(ChatTopicUser.topic_id, ChatTopicUser.vcpid)
        .filter(ChatTopicUser.topic_id.in_(my_topic_ids))
        .all()
    )

    # Map: vcpid → list of topic_ids shared with current user
    from collections import defaultdict
    shared_topics = defaultdict(list)
    for topic_id, vcpid in topic_user_map:
        if vcpid != current_vcpid:
            shared_topics[vcpid].append(topic_id)

    # Step 5: Fetch topic names for group topic tooltip
    topic_names = dict(
        db.session.query(ChatTopic.id, ChatTopic.name).filter(ChatTopic.id.in_(my_topic_ids)).all()
    )

    # Step 6: Build contacts list
    contacts = []
    for user in active_users:
        vcpid = user.vcpid
        profile = profcv_lookup.get(vcpid, {})

        topics = shared_topics.get(vcpid, [])
        has_private_chat = len(topics) == 1
        has_group_chat = len(topics) > 1

        contact = {
            "id": user.ID,
            "vcpid": vcpid,
            "fullname": user.fullname,
            "email": user.email,
            "public_name": profile.get("public_name", user.fullname),
            "public_title": profile.get("public_title", ""),
            "location": profile.get("location", ""),
            "has_private_chat": has_private_chat,
            "has_group_chat": has_group_chat,
            "shared_topic_names": [topic_names[tid] for tid in topics if tid in topic_names]
        }
        contacts.append(contact)

    return render_template("cnts.html", contacts=contacts)

@cnts_bp.route('/create_chat_topic', methods=['POST'])
@login_required
def create_chat_topic():
    from ..models import ChatTopic, ChatTopicUser

    data = request.get_json()
    other_vcpid = data.get('vcpid')
    current_vcpid = session.get('vcpid')

    if not other_vcpid or other_vcpid == current_vcpid:
        return jsonify({"success": False, "message": "Invalid request."})

    # Check if private topic already exists
    from sqlalchemy import func

    topic_ids_user1 = db.session.query(ChatTopicUser.topic_id).filter_by(vcpid=current_vcpid).subquery()
    topic_ids_user2 = db.session.query(ChatTopicUser.topic_id).filter_by(vcpid=other_vcpid).subquery()

    common_topic = (
        db.session.query(ChatTopicUser.topic_id)
        .filter(ChatTopicUser.topic_id.in_(topic_ids_user1))
        .filter(ChatTopicUser.topic_id.in_(topic_ids_user2))
        .group_by(ChatTopicUser.topic_id)
        .having(func.count(ChatTopicUser.vcpid) == 2)
        .first()
    )

    if common_topic:
        return jsonify({"success": True, "message": "Chat already exists."})

    # Create new chat topic
    topic = ChatTopic(name=f"Chat_{current_vcpid}_{other_vcpid}", created_by_vcpid=current_vcpid)
    db.session.add(topic)
    db.session.flush()  # to get topic.id

    db.session.add_all([
        ChatTopicUser(topic_id=topic.id, vcpid=current_vcpid),
        ChatTopicUser(topic_id=topic.id, vcpid=other_vcpid)
    ])
    db.session.commit()

    return jsonify({"success": True, "message": "Chat created successfully."})
