# task_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, date
from ..models import db, Vemp, ChatTopic, ChatTopicUser, ChatMessage

from sqlalchemy.orm import joinedload #learn more about it


chat_bp = Blueprint('chat', __name__)

from functools import wraps
def login_required(view):
  @wraps(view)
  def wrapped_view(**kwargs):
    if 'user_code' not in session:
      flash("Please log in to access this page.", 'info')
      return redirect(url_for('auth.login'))
    return view(**kwargs)
  return wrapped_view


@chat_bp.route('/chat', methods=['GET', 'POST'])
@login_required
def chat_home():
    current_user_id = session.get("user_id")  # Assuming login system sets this

    # Get topics the user is part of, and prefetch messages and users
    topics = (
        db.session.query(ChatTopic)
        .join(ChatTopicUser)
        .filter(ChatTopicUser.user_id == current_user_id)
        .options(
            joinedload(ChatTopic.messages).joinedload(ChatMessage.sender),
            joinedload(ChatTopic.users)  # You define ChatTopic.users as backref
        )
        .all()
    )

    # Prepare topic data for the template
    topics_data = []
    for topic in topics:
        # One-to-one topic: show other person's name
        if len(topic.users) == 2:
            other_user = next(u for u in topic.users if u.id != current_user_id)
            display_name = other_user.fullname
        else:
            display_name = topic.name

        messages = [
            {
                "sender": msg.sender.fullname,
                "message": msg.message,
                "sent_at": msg.sent_at.strftime("%Y-%m-%d %H:%M"),
            }
            for msg in sorted(topic.messages, key=lambda m: m.sent_at)
        ]

        topics_data.append({
            "id": topic.id,
            "name": display_name,
            "messages": messages,
        })

    return render_template("chat.html", topics=topics_data, current_user_id=current_user_id)



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