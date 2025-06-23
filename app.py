# app.py
import os
import pyodbc
from datetime import date, datetime, timedelta
import uuid
from flask_sqlalchemy import SQLAlchemy

from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask application
app = Flask(__name__)
# Set a secret key for session management. VERY IMPORTANT for security.
# In a real application, this should be a strong, randomly generated string
# and stored securely (e.g., environment variable).
app.secret_key = os.urandom(24) # Generates a random 24-byte key
app.permanent_session_lifetime = timedelta(days=1) # Session valid for 1 day
# Define the database file path (MS Access .accdb)
DATABASE = r'C:\Users\Hp\My Drive\Z-DataFiles\rcPro.accdb'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://rax:512@localhost/rcmain'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Avoids a warning
# Create SQLAlchemy instance
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    # Add a backref/relationship if you haven't already, e.g.:
    tasks = db.relationship('Task', backref='owner', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

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

def get_db():
    """Establishes a database connection or returns the existing one."""
    if 'db' not in g:
        conn_str = (
            r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
            f'DBQ={DATABASE};'
        )
        g.db = pyodbc.connect(conn_str)
    return g.db

def close_db():
    """Closes the database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """No-op for MS Access: assumes tables already exist."""
    pass
# Define the database file path
DATABASE = r'C:\Users\Hp\My Drive\Z-DataFiles\rcPro.accdb'

# Register database functions with the Flask app
#This decorator ensures that the teardown_db function will be called automatically at the very end of a request, right before the application context is removed.
@app.teardown_appcontext
def teardown_db(_):
    close_db()



# --- Authentication Decorator ---

def login_required(view):
    """Decorator to ensure a user is logged in before accessing a view."""
    import functools
    
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
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


# --- Routes ---

@app.route('/')
def index():
    """Redirects to dashboard if logged in, otherwise to login page."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=('GET', 'POST'))
def login():
    """Handles user login."""
    if 'user_id' in session:
        return redirect(url_for('dashboard')) # Redirect if already logged in

    if request.method == 'POST':
        email = request.form['email'].strip()
        pin = request.form['pin'].strip()
        error = None

        db = get_db()
        user = db.execute(
            'SELECT code,email,pin_hash FROM vemp WHERE email = ?', (email,)
        ).fetchone()

        if user is None:
            error = "Incorrect email or PIN."
        elif not check_password_hash(user[2], pin):  # Assuming pin_hash is the third column

            error = "Incorrect email or PIN."

        if error is None:
            session.clear()
            session['user_id'] = user[0]  # Assuming id is the first column
            session['user_email'] = user[1]  # Assuming email is the second column
            session.permanent = True # Make the session permanent (for 1 day)
            flash(f"Welcome back, {user[1]}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(error, 'danger')

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Displays the user dashboard."""
    print(session['user_id'])
    db = get_db()
    user = db.execute(
        'SELECT email,fullname FROM vemp WHERE code = ?', (session['user_id'],)
    ).fetchone()
    # Extract name from email if needed, or just display the email
    # user_name = user[1]


    # Fetch tasks for the current user
    user_tasks = Task.query.filter_by(user_id=1).order_by(Task.due_date.asc()).all()

    # Add a 'due_soon' flag for styling
    for t in user_tasks:
        if t.due_date:
            days_left = (t.due_date - date.today()).days
            t.due_soon = (days_left >= 0 and days_left <= 3) and t.status != 'Completed'
        else:
            t.due_soon = False

    return render_template('dashboard.html', user_name="john_doe", tasks=user_tasks)


@app.route('/logout')
def logout():
    """Logs out the user by clearing the session."""
    session.clear()
    flash("You have been logged out.", 'info')
    return redirect(url_for('login'))

@app.route('/forgot_pin', methods=('GET', 'POST'))

def forgot_pin():
    """Initiates the PIN reset process."""
    if request.method == 'POST':
        email = request.form['email'].strip()
        db = get_db()
        user = db.execute(
            'SELECT * FROM vemp WHERE email = ?', (email,)
        ).fetchone()
        print("enter forgot_pin")
        if user:
            # Generate a unique token and set an expiration time
            reset_token = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(hours=1) # Token valid for 1 hour
            db.execute(
                'UPDATE vemp SET reset_token = ?, reset_token_expires_at = ? WHERE id = ?',
                (reset_token, expires_at, user[0])
            )
            db.commit()
            

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
    """Allows setting a new PIN using a reset token."""
    db = get_db()
    user = db.execute(
        'SELECT code,email,reset_token_expires_at FROM vemp WHERE reset_token = ?', (token,)
    ).fetchone()

    if not user:
        flash("Invalid or expired PIN reset link.", 'danger')
        return redirect(url_for('login'))

    # Check if token has expired
    expires_at = user[2]  # Assuming reset_token_expires_at is the 3rd column
    
    if expires_at:
        if isinstance(expires_at, str):
            
            print("ehere")
            fmt = "%m/%d/%Y %I:%M:%S %p"
            expires_at = datetime.strptime(expires_at, fmt)
            print(expires_at)
            # Try multiple formats to parse the datetime string
        print(datetime.now() > expires_at)        
        if (datetime.now() > expires_at):
            # Clear the expired token
            db.execute(
            'UPDATE vemp SET reset_token = NULL, reset_token_expires_at = NULL WHERE id = ?',
            (user[0],)
            )
            db.commit()
            flash("Your PIN reset link has expired. Please request a new one.", 'danger')
            return redirect(url_for('forgot_pin'))
        # else: token is valid, allow user to set new PIN (do nothing, continue to form)

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
            print(hashed_pin,user[0])
            
            db.execute(
                'UPDATE vemp SET pin_hash = ?, reset_token = NULL, reset_token_expires_at = NULL WHERE code = ?',
                (hashed_pin, user[0])
            )            
            db.commit()
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
            new_task = Task(name=task_name, description=description, due_date=due_date, user_id=1)
            db.session.add(new_task)
            db.session.commit()
            flash('Task added successfully!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('add_edit_task.html', title='Add Task')

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)

    # Ensure the logged-in user owns this task
    if task.user_id != 1:
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
    task = task.query.get_or_404(task_id)
    if task.user_id != 1:
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
    if task.user_id != 1:
        flash('You are not authorized to delete this task.', 'danger')
    else:
        db.session.delete(task)
        db.session.commit()
        flash('Task deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

# For demo purposes, let's create a dummy user upon first run if no users exist
@app.before_request
def check_for_users():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM vemp")
    count = cursor.fetchone()[0]
    if count == 0:
        print("No users found. Creating a default user: user@example.com with PIN 1234")
        # Hash '1234'
        hashed_pin = generate_password_hash('1234')
        try:
            db.execute(
                "INSERT INTO vemp (email, pin_hash) VALUES (?, ?)",
                ('user@example.com', hashed_pin)
            )
            db.commit()
            print("Default user created.")
        except pyodbc.IntegrityError:
            print("Default user already exists (likely due to previous run).")


if __name__ == '__main__':
    app.run(debug=True) # debug=True is for development only. Set to False for production.

