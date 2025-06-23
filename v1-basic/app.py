# app.py
import os
from datetime import date, datetime, timedelta
import uuid
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask application

app = Flask(__name__)

# Set a secret key for session management. VERY IMPORTANT for security.
# In a real application, this should be a strong, randomly generated string
# and stored securely (e.g., environment variable).

# Use a constant secret key for session persistence (change this in production!)
app.secret_key = os.urandom(24).hex()  # Generates a random 48-character hex key each run
app.permanent_session_lifetime = timedelta(days=1) # Session valid for 1 day
# Define the database file path (MS Access .accdb)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://rax:512@localhost/rcmain'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Avoids a warning

# Create SQLAlchemy instance
db = SQLAlchemy(app)

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
    user_code = db.Column(db.String(6), nullable=False) # Link to the user
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='Pending') # e.g., 'Pending', 'Completed'
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    def __repr__(self):
        return f'<Task {self.name}>'

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
@app.route('/')
def index():
  """Redirects to dashboard if logged in, otherwise to login page."""
  print("Session variables:", dict(session))
  if 'user_code' in session:
    return redirect(url_for('dashboard'))
  return redirect(url_for('login'))


@app.route('/login', methods=('GET', 'POST'))
def login():
  """Handles user login."""

  if 'user_code' in session:
    return redirect(url_for('dashboard'))  # Redirect if already logged in

  if request.method == 'POST':
    email = request.form.get('email', '').strip()
    pin = request.form.get('pin', '').strip()
    error = None

    user = Vemp.query.filter_by(email=email).first()

    if not user or not user.pin_hash or not check_password_hash(user.pin_hash, pin):
      error = "Incorrect email or PIN."

    if error is None:
      session.clear()
      session.permanent = True  # Make the session permanent (for 1 day)
      session['user_code'] = user.code  # Use user.code as the unique identifier
      session['user_email'] = user.email
      flash(f"Welcome back, {user.fullname or user.email}!", 'success')
      return redirect(url_for('dashboard'))
    else:
      flash(error, 'danger')
  
  return render_template('login.html')

@app.route('/dashboard')
@login_required

def dashboard():
  """Displays the user dashboard."""
  user_code = session.get('user_code')
  user = Vemp.query.filter_by(code=user_code).first()
  if not user:
    flash("User not found.", "danger")
    return redirect(url_for('logout'))

  # Fetch tasks for the current user
  user_tasks = Task.query.filter_by(user_code=user_code).order_by(Task.due_date.asc()).all()
  for t in user_tasks:
    if t.due_date:
      days_left = (t.due_date - date.today()).days
      t.due_soon = (0 <= days_left <= 3) and t.status != 'Completed'
    else:
      t.due_soon = False

  return render_template('dashboard.html', user_name=user.fullname or user.email, tasks=user_tasks)





@app.route('/logout')
def logout():
  """Logs out the user by clearing the session."""
  session.clear()
  flash("You have been logged out.", 'info')
  return redirect(url_for('login'))



@app.route('/forgot_pin', methods=('GET', 'POST'))

def forgot_pin():
  """Initiates the PIN reset process using SQLAlchemy (Vemp)."""
  if request.method == 'POST':
    email = request.form['email'].strip()
    user = Vemp.query.filter_by(email=email).first()
    print("enter forgot_pin")

    if user:
      # Generate a unique token and set an expiration time
      reset_token = str(uuid.uuid4())
      expires_at = datetime.now() + timedelta(hours=1) # Token valid for 1 hour

      user.reset_token = reset_token
      user.reset_token_expires_at = expires_at
      db.session.commit()

      # --- Simulate sending email ---
      reset_link = url_for('set_pin', token=reset_token, _external=True)
      print(f"\n--- PIN Reset Link (SIMULATED EMAIL) ---\n"
            f"To: {email}\n"
            f"Subject: Your PIN Reset Request\n"
            f"Click the link to set your new PIN: {reset_link}\n"
            f"----------------------------------------\n")
      flash("A PIN reset link has been sent to your email (check console for link).", 'success')
      return render_template('message.html', message="PIN reset link sent!")
    else:
      flash("No account found with that email.", 'danger')

  return render_template('forgot_pin.html')



@app.route('/set_pin/<token>', methods=('GET', 'POST'))
def set_pin(token):
  """Allows setting a new PIN using a reset token (SQLAlchemy version)."""
  user = Vemp.query.filter_by(reset_token=token).first()

  if not user:
    flash("Invalid or expired PIN reset link.", 'danger')
    return redirect(url_for('login'))

  expires_at = user.reset_token_expires_at

  if expires_at:
    if datetime.now() > expires_at:
      # Clear the expired token
      user.reset_token = None
      user.reset_token_expires_at = None
      db.session.commit()
      flash("Your PIN reset link has expired. Please request a new one.", 'danger')
      return redirect(url_for('forgot_pin'))

  if request.method == 'POST':
    new_pin = request.form['new_pin'].strip()
    confirm_pin = request.form['confirm_pin'].strip()
    error = None

    if len(new_pin) != 4 or not new_pin.isdigit():
      error = "PIN must be a 4-digit number."
    elif new_pin != confirm_pin:
      error = "PINs do not match."

    if error is None:
      hashed_pin = generate_password_hash(new_pin)
      user.pin_hash = hashed_pin
      user.reset_token = None
      user.reset_token_expires_at = None
      db.session.commit()
      flash("Your PIN has been successfully set. You can now log in.", 'success')
      return redirect(url_for('login'))
    else:
      flash(error, 'danger')

  return render_template('set_pin.html', token=token)



@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
  if request.method == 'POST':
    task_name = request.form.get('task_name')
    due_date_str = request.form.get('due_date')
    description = request.form.get('description')
    due_date = None
    if due_date_str:
      try:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
      except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
        return render_template('add_edit_task.html', title='Add Task')



    if not task_name:
      flash('Task name cannot be empty!', 'danger')
    else:
      user_code= session.get('user_code')  # Default to '1' if not set
      new_task = Task(name=task_name, description=description, due_date=due_date, user_code=user_code)
      db.session.add(new_task)
      db.session.commit()
      flash('Task added successfully!', 'success')
      return redirect(url_for('dashboard'))

  return render_template('add_edit_task.html', title='Add Task')



@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
  task = Task.query.get_or_404(task_id)
  user_code= session.get('user_code')  # Default to '1' if not set
  # Ensure the logged-in user owns this task
  if task.user_code != user_code:
    flash('You are not authorized to edit this task.', 'danger')
    return redirect(url_for('dashboard'))
  if request.method == 'POST':
    task.name = request.form.get('task_name')
    due_date_str = request.form.get('due_date')
    task.description = request.form.get('description')
    task.status = request.form.get('status')

    if due_date_str:
      try:
        task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
      except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
        return render_template('add_edit_task.html', title='Edit Task', task=task)
    else:
      task.due_date = None # Allow clearing the due date


    if not task.name:
      flash('Task name cannot be empty!', 'danger')
    else:
      db.session.commit()
      flash('Task updated successfully!', 'success')
      return redirect(url_for('dashboard'))


  return render_template('add_edit_task.html', title='Edit Task', task=task)



@app.route('/mark_task_complete/<int:task_id>')
@login_required
def mark_task_complete(task_id):
  print("hi")
  task = Task.query.get_or_404(task_id)
  if task.user_code != session.get('user_code'):
    flash('You are not authorized to modify this task.', 'danger')
  else:
    task.status = 'Completed'
    db.session.commit()
    flash('Task marked as complete!', 'success')

  return redirect(url_for('dashboard'))



@app.route('/delete_task/<int:task_id>')

@login_required
def delete_task(task_id):
  task = Task.query.get_or_404(task_id)
  if task.user_code != session.get('user_code'):
    flash('You are not authorized to delete this task.', 'danger')
  else:
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!', 'success')

  return redirect(url_for('dashboard'))



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



if __name__ == '__main__':
  app.run(debug=True) # debug=True is for development only. Set to False for production.



