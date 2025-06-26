# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()

class Vemp(db.Model):
    __tablename__ = 'vemp'

    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(20), nullable=True)
    fullname = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), nullable=True)
    cvxml = db.Column(db.Text, nullable=True)
    email = db.Column(db.String(100), nullable=True)
    pin_hash = db.Column(db.String(255), nullable=True)
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<Vemp {self.ID} - {self.fullname}>"


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_code = db.Column(db.String(6), nullable=False)
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
    

    def __repr__(self):
        return f'<Profcv {self.name}>'

