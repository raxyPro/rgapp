# my_flask_app/models.py

from . import db # Import the db instance from the main app package
from datetime import datetime

class User(db.Model):
    __tablename__ = 'user' # Explicitly set table name to 'user' for clarity
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False) # This is not used by your Access login, but for MySQL User if you expand
    tasks = db.relationship('Task', backref='owner', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

class Task(db.Model):
    __tablename__ = 'task' # Explicitly set table name to 'task'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Link to the MySQL user.id
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='Pending')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f'<Task {self.name}>'