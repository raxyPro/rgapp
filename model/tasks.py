# models.py (or integrated into your main app.py)
import pystock_conf as pc
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

engine = pc.GetSQALCon()
db = SQLAlchemy()
db.engine = engine

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Link to the user
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='Pending') # e.g., 'Pending', 'Completed'
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f'<Task {self.name}>'