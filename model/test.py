import pystock_conf as pc
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

engine = pc.GetSQALCon()
db = SQLAlchemy()
db.engine = engine

class Task(db.Model):
    __tablename__ = 'tasks' # Optional: explicitly define table name

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True) # Text allows longer strings
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed = db.Column(db.Boolean, default=False)

    def __repr__(self):
        """
        Defines how a Task object is represented when printed.
        Useful for debugging.
        """
        return f"Task(id={self.id}, title='{self.title}', completed={self.completed})"

    def to_dict(self):
        """
        Converts the Task object to a dictionary for JSON serialization.
        """
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'created_at': self.created_at.isoformat(), # Convert datetime to ISO string
            'completed': self.completed
        }

if __name__ == "__main__":

    # Create a sample Task instance
    sample_task = Task(
        title="Sample Task",
        description="This is a sample task.",
        created_at=datetime.utcnow(),
        completed=False
    )

    # Print the Task object
    print(sample_task)

    # Print the dictionary representation
    print(sample_task.to_dict())