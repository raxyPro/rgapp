# app.py
import os
from datetime import date, datetime, timedelta
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, Vemp, Task  # ← Import from models.py

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()
app.permanent_session_lifetime = timedelta(days=1)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://rax:512@localhost/rcmain'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)  # ← Initialize db with app
# Register database functions with the Flask app

#This decorator ensures that the teardown_db function will be called automatically at the very end of a request, right before the application context is removed.

@app.teardown_appcontext
def teardown_db(_):
  db.session.remove()

# --- Authentication Decorator ---
#-- i do not undersand it but let us leave it for time being
def login_required(view):
  """Decorator to ensure a user is logged in before accessing a view."""
  import functools
  @functools.wraps(view)
  def wrapped_view(**kwargs):
    if 'user_code' not in session:
      flash("Please log in to access this page.", 'info')
      return redirect(url_for('login'))
    return view(**kwargs)
  return wrapped_view

# --- Global Context Processor ---

# this injects variables into all templates - great feature for common data like current year

@app.context_processor
def inject_current_year():
  """Injects the current year into all templates."""
  return {'current_year': datetime.now().year}

# --- Routes --- this is where we define the routes for our application the request comes from HTML

# For demo purposes, let's create a dummy user upon first run if no users exist

@app.before_request
def check_for_users():
  if Vemp.query.count() == 0:
    print("No users found. Creating a default user: user@example.com with PIN 1234")
    hashed_pin = generate_password_hash('1234')
    default_user = Vemp(email='user@example.com', pin_hash=hashed_pin)
    db.session.add(default_user)
    db.session.commit()
    print("Default user created.")


from auth_routes import auth_bp
from task_routes import task_bp
from prof_routes import prof_bp

app.register_blueprint(auth_bp)
app.register_blueprint(task_bp)
app.register_blueprint(prof_bp)

if __name__ == '__main__':
  app.run(debug=True) # debug=True is for development only. Set to False for production.



