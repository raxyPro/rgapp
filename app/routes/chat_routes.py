# task_routes.py
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, session
from datetime import datetime, date
from ..models import db, Vemp, ChatTopic, ChatTopicUser, ChatMessage

from sqlalchemy.orm import joinedload #learn more about it


chat_bp = Blueprint('chat', __name__)

from functools import wraps
def login_required(view):
  @wraps(view)
  def wrapped_view(**kwargs):
    if 'vcpid' not in session:
      flash("Please log in to access this page.", 'info')
      return redirect(url_for('auth.login'))
    return view(**kwargs)
  return wrapped_view


@chat_bp.route('/send_message', methods=['GET', 'POST'])
@login_required
def sendMessage():
    data = request.get_json()

    topic_id = data.get('topic_id')
    message_text = data.get('message')
    sender_id = session.get('user_id')

    if not sender_id or not topic_id or not message_text:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400

    try:
        new_message = ChatMessage(
            topic_id=topic_id,
            sender_id=sender_id,
            message=message_text,
            sent_at=datetime.utcnow()
        )
        db.session.add(new_message)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500



@chat_bp.route('/chat-test')
def sample_transaction():
    try:
        # Start a transaction using ChatManager class
        from ..models import ChatManager, Vemp  # Import ChatManager and Vemp from your models
        manager = ChatManager(db)

        # Fetch two valid user IDs from the Vemp table
        users = Vemp.query.limit(2).all()
        if len(users) < 2:
            raise Exception("Not enough users in the database to create a chat topic.")

        creator_id = users[0].ID  # Use actual column name for primary key
        user_id_2 = users[1].ID

        # Create topic
        topic = manager.create_topic("Rampal", creator_id)
        print("Created Topic:", topic.name)

        # Add users to topic
        manager.add_user_to_topic(topic.id, creator_id)
        manager.add_user_to_topic(topic.id, user_id_2)
        print(f"Added users {creator_id} and {user_id_2} to topic {topic.name}")

        # Send message
        message = manager.send_message(topic.id, creator_id, "Welcome to the team chat!")
        print("Sent Message:", message.message)

        db.session.commit()
        flash(f"Chat transaction successful: Topic '{topic.name}' created and message sent.", "success")


    except Exception as e:
        db.session.rollback()
        flash(f"Transaction failed: {str(e)}", "danger")

    return render_template('chat.html', message="Sample transaction attempted.")