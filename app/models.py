from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime

db = SQLAlchemy()

class Vemp(db.Model):
    __tablename__ = 'vemp'

    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vcpid = db.Column(db.String(6), nullable=True)
    user_id = db.Column(db.Integer, nullable=False)
    fullname = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), nullable=True)
    cvxml = db.Column(db.Text, nullable=True)
    email = db.Column(db.String(100), nullable=True)
    user_role = db.Column(db.String(20), nullable=True)
    pin_hash = db.Column(db.String(255), nullable=True)
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<Vemp {self.ID} - {self.fullname}>"


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vcpid = db.Column(db.String(6), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='Pending')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f'<Task {self.name}>'


class Profcv(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    pf_typ = db.Column(db.String(200))
    pf_name = db.Column(db.Text)
    pf_data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f'<Profcv {self.pf_name}>'


class ChatTopic(db.Model):
    __tablename__ = 'chat_topic'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_by_vcpid = db.Column(db.String(6), db.ForeignKey('vemp.ID'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship('ChatTopicUser', back_populates='topic', cascade='all, delete-orphan')
    messages = db.relationship('ChatMessage', back_populates='topic', cascade='all, delete-orphan')


class ChatTopicUser(db.Model):
    __tablename__ = 'chat_topic_user'

    topic_id = db.Column(db.Integer, db.ForeignKey('chat_topic.id'), primary_key=True)
    vcpid = db.Column(db.String(6), db.ForeignKey('vemp.vcpid'), primary_key=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    topic = db.relationship('ChatTopic', back_populates='users')
    user = db.relationship('Vemp', primaryjoin="ChatTopicUser.vcpid == Vemp.vcpid")

    @property
    def fullname(self):
        return self.user.fullname if self.user else None

class TaskManager:
    def __init__(self, db_session):
        self.db = db_session

    def get_tasks_by_user(self,  vcpid: str):
        user_tasks = Task.query.filter_by(vcpid=vcpid).order_by(Task.due_date.asc()).all()
        
        for t in user_tasks:
            if t.due_date:
                days_left = (t.due_date - date.today()).days
                t.due_soon = (0 <= days_left <= 3) and t.status != 'Completed'
            else:
                t.due_soon = False
        return user_tasks
    
class ChatMessage(db.Model):
    __tablename__ = 'chat_message'

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('chat_topic.id'), nullable=False)
    sender_vcpid = db.Column(db.String(6), db.ForeignKey('vemp.vcpid'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    topic = db.relationship('ChatTopic', back_populates='messages')
    sender = db.relationship('Vemp', primaryjoin="ChatMessage.sender_vcpid == Vemp.vcpid")



class ChatManager:
    def __init__(self, db_session):
        self.db = db_session

    def create_topic(self, name: str, creator_id: int):
        topic = ChatTopic(name=name, created_by=creator_id)
        self.db.session.add(topic)
        self.db.session.commit()
        return topic

    def add_user_to_topic(self, topic_id: int, user_id: int):
        link = ChatTopicUser(topic_id=topic_id, user_id=user_id)
        self.db.session.add(link)
        self.db.session.commit()
        return link

    def send_message(self, topic_id: int, sender_id: int, message: str):
        msg = ChatMessage(topic_id=topic_id, sender_id=sender_id, message=message)
        self.db.session.add(msg)
        self.db.session.commit()
        return msg
from datetime import datetime

class ChatManager:
    def __init__(self, db_session):
        self.db = db_session

    def get_chats_by_user(self, vcpid: str):
        topics = (
            self.db.query(ChatTopic)
            .join(ChatTopicUser)
            .filter(ChatTopicUser.vcpid == vcpid)
            .options(
                db.joinedload(ChatTopic.messages).joinedload(ChatMessage.sender),
                db.joinedload(ChatTopic.users)
            )
            .all()
        )

        #user_fullnames = []
        #for u in topic.users:
        #    user_obj = self.db.query(Vemp).filter_by(id=u.user_id).first()
        #    user_fullnames.append(user_obj.fullname if user_obj else "Unknown")

        chat_list = []
        for topic in topics:
            # Determine topic display name
            if len(topic.users) == 2:
                # One-to-one chat: show the other person's name (not the current user)
                other_user = next((u for u in topic.users if u.id != vcpid), None)
                display_name = other_user.fullname if other_user else topic.name
            else:
                # Group topic: show actual topic name
                display_name = topic.name

            chat_list.append({
                "id": topic.id,
                "name": display_name,
                "users": [u.fullname for u in topic.users],
                "messages": [
                    {
                        "sender": msg.sender.fullname,
                        "message": msg.message,
                        "sent_at": msg.sent_at.strftime("%Y-%m-%d %H:%M")
                    }
                    for msg in sorted(topic.messages, key=lambda m: m.sent_at)
                ]
            })

        return chat_list
