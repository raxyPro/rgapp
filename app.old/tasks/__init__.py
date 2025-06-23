# my_flask_app/tasks/__init__.py
from flask import Blueprint

tasks_bp = Blueprint('tasks', __name__)

from . import routes # Import routes to register them with the blueprint