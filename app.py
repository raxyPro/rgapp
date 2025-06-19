# app.py
import os
import pyodbc
from datetime import datetime, timedelta
import uuid

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

def get_db():
    """Establishes a database connection or returns the existing one."""
    if 'db' not in g:
        conn_str = (
            r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
            f'DBQ={DATABASE};'
        )
        g.db = pyodbc.connect(conn_str)
    return g.db

def close_db(e=None):
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
@app.teardown_appcontext
def teardown_db(exception):
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
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()

        if user is None:
            error = "Incorrect email or PIN."
        elif not check_password_hash(user['pin_hash'], pin):
            error = "Incorrect email or PIN."

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session.permanent = True # Make the session permanent (for 1 day)
            flash(f"Welcome back, {user['email']}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(error, 'danger')

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Displays the user dashboard."""
    db = get_db()
    user = db.execute(
        'SELECT email FROM users WHERE id = ?', (session['user_id'],)
    ).fetchone()
    # Extract name from email if needed, or just display the email
    user_name = user['email'].split('@')[0] if user else 'User'
    return render_template('dashboard.html', user_name=user_name)

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
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()

        if user:
            # Generate a unique token and set an expiration time
            reset_token = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(hours=1) # Token valid for 1 hour

            db.execute(
                'UPDATE users SET reset_token = ?, reset_token_expires_at = ? WHERE id = ?',
                (reset_token, expires_at, user['id'])
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
        'SELECT * FROM users WHERE reset_token = ?', (token,)
    ).fetchone()

    if not user:
        flash("Invalid or expired PIN reset link.", 'danger')
        return redirect(url_for('login'))

    # Check if token has expired
    expires_at = user['reset_token_expires_at']
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S.%f')
        if datetime.now() > expires_at:
            # Clear the expired token
            db.execute(
                'UPDATE users SET reset_token = NULL, reset_token_expires_at = NULL WHERE id = ?',
                (user['id'],)
            )
            db.commit()
            flash("Your PIN reset link has expired. Please request a new one.", 'danger')
            return redirect(url_for('forgot_pin'))
        # Clear the expired token
        db.execute(
            'UPDATE users SET reset_token = NULL, reset_token_expires_at = NULL WHERE id = ?',
            (user['id'],)
        )
        db.commit()
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
            db.execute(
                'UPDATE users SET pin_hash = ?, reset_token = NULL, reset_token_expires_at = NULL WHERE id = ?',
                (hashed_pin, user['id'])
            )
            db.commit()
            flash("Your PIN has been successfully set. You can now log in.", 'success')
            return redirect(url_for('login'))
        else:
            flash(error, 'danger')

    return render_template('set_pin.html', token=token)

# --- Templating (HTML Files) ---
# These will be in the 'templates/' directory

# templates/layout.html
# This is the base template for consistent header and footer.
# It includes Tailwind CSS for basic styling.
# NOTE: Tailwind CSS is loaded via CDN for simplicity.
# For a production app, you'd integrate it properly with PostCSS.
layout_html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}My App{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .flash {
            padding: 0.75rem 1.25rem;
            margin-bottom: 1rem;
            border: 1px solid transparent;
            border-radius: 0.25rem;
        }
        .flash.success {
            color: #155724;
            background-color: #d4edda;
            border-color: #c3e6cb;
        }
        .flash.danger {
            color: #721c24;
            background-color: #f8d7da;
            border-color: #f5c6cb;
        }
        .flash.info {
            color: #0c5460;
            background-color: #d1ecf1;
            border-color: #bee5eb;
        }
    </style>
</head>
<body class="bg-gray-100 flex flex-col min-h-screen">
    <header class="bg-gradient-to-r from-blue-600 to-indigo-700 text-white p-4 shadow-md">
        <div class="container mx-auto flex justify-between items-center">
            <h1 class="text-3xl font-bold rounded-md">
                <a href="{{ url_for('index') }}" class="hover:text-blue-200 transition duration-300">My Secure App</a>
            </h1>
            <nav>
                <ul class="flex space-x-6 text-lg">
                    {% if 'user_id' in session %}
                        <li><a href="{{ url_for('dashboard') }}" class="hover:text-blue-200 transition duration-300">Dashboard</a></li>
                        <li><a href="{{ url_for('logout') }}" class="hover:text-blue-200 transition duration-300">Logout</a></li>
                    {% else %}
                        <li><a href="{{ url_for('login') }}" class="hover:text-blue-200 transition duration-300">Login</a></li>
                    {% endif %}
                </ul>
            </nav>
        </div>
    </header>

    <main class="container mx-auto mt-8 p-4 flex-grow">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="mb-4">
                    {% for category, message in messages %}
                        <div class="flash {{ category }} rounded-md shadow-sm" role="alert">
                            {{ message }}
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </main>

    <footer class="bg-gray-800 text-white p-4 text-center mt-8 shadow-inner">
        <div class="container mx-auto">
            <p>&copy; {{ current_year }} My Secure App. All rights reserved.</p>
        </div>
    </footer>
</body>
</html>
"""

# templates/login.html
login_html_content = """
{% extends 'layout.html' %}

{% block title %}Login{% endblock %}

{% block content %}
<div class="flex items-center justify-center min-h-full py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8 p-10 bg-white rounded-xl shadow-lg border border-gray-200">
        <div class="text-center">
            <h2 class="mt-6 text-3xl font-extrabold text-gray-900 rounded-md">
                Log in to your account
            </h2>
        </div>
        <form class="mt-8 space-y-6" method="POST">
            <div class="rounded-md shadow-sm -space-y-px">
                <div>
                    <label for="email" class="sr-only">Email address</label>
                    <input id="email" name="email" type="email" autocomplete="email" required
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                           placeholder="Email address">
                </div>
                <div>
                    <label for="pin" class="sr-only">4-digit PIN</label>
                    <input id="pin" name="pin" type="password" maxlength="4" pattern="[0-9]{4}" title="Please enter a 4-digit number" required
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                           placeholder="4-digit PIN">
                </div>
            </div>

            <div class="flex items-center justify-between">
                <div class="text-sm">
                    <a href="{{ url_for('forgot_pin') }}" class="font-medium text-indigo-600 hover:text-indigo-500 transition duration-300">
                        Forgot/Set PIN?
                    </a>
                </div>
            </div>

            <div>
                <button type="submit"
                        class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-300 shadow-md">
                    Sign in
                </button>
            </div>
        </form>
    </div>
</div>
{% endblock %}
"""

# templates/dashboard.html
dashboard_html_content = """
{% extends 'layout.html' %}

{% block title %}Dashboard{% endblock %}

{% block content %}
<div class="text-center p-8 bg-white rounded-xl shadow-lg border border-gray-200">
    <h2 class="text-4xl font-extrabold text-gray-900 mb-4">Welcome, {{ user_name }}!</h2>
    <p class="text-lg text-gray-600">You are successfully logged in to your personalized dashboard.</p>
    <div class="mt-8">
        <a href="{{ url_for('logout') }}" class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-full shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition duration-300">
            Logout
        </a>
    </div>
</div>
{% endblock %}
"""

# templates/forgot_pin.html
forgot_pin_html_content = """
{% extends 'layout.html' %}

{% block title %}Forgot/Set PIN{% endblock %}

{% block content %}
<div class="flex items-center justify-center min-h-full py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8 p-10 bg-white rounded-xl shadow-lg border border-gray-200">
        <div class="text-center">
            <h2 class="mt-6 text-3xl font-extrabold text-gray-900 rounded-md">
                Forgot or Set PIN
            </h2>
            <p class="mt-2 text-sm text-gray-600">
                Enter your email address and we'll send you a link to set your PIN.
            </p>
        </div>
        <form class="mt-8 space-y-6" method="POST">
            <div class="rounded-md shadow-sm -space-y-px">
                <div>
                    <label for="email" class="sr-only">Email address</label>
                    <input id="email" name="email" type="email" autocomplete="email" required
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                           placeholder="Email address">
                </div>
            </div>

            <div>
                <button type="submit"
                        class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-300 shadow-md">
                    Send PIN Set Link
                </button>
            </div>
        </form>
    </div>
</div>
{% endblock %}
"""

# templates/set_pin.html
set_pin_html_content = """
{% extends 'layout.html' %}

{% block title %}Set Your PIN{% endblock %}

{% block content %}
<div class="flex items-center justify-center min-h-full py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8 p-10 bg-white rounded-xl shadow-lg border border-gray-200">
        <div class="text-center">
            <h2 class="mt-6 text-3xl font-extrabold text-gray-900 rounded-md">
                Set Your New 4-digit PIN
            </h2>
        </div>
        <form class="mt-8 space-y-6" method="POST">
            <div class="rounded-md shadow-sm -space-y-px">
                <div>
                    <label for="new_pin" class="sr-only">New 4-digit PIN</label>
                    <input id="new_pin" name="new_pin" type="password" maxlength="4" pattern="[0-9]{4}" title="Please enter a 4-digit number" required
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                           placeholder="New 4-digit PIN">
                </div>
                <div>
                    <label for="confirm_pin" class="sr-only">Confirm 4-digit PIN</label>
                    <input id="confirm_pin" name="confirm_pin" type="password" maxlength="4" pattern="[0-9]{4}" title="Please confirm your 4-digit number" required
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                           placeholder="Confirm 4-digit PIN">
                </div>
            </div>

            <div>
                <button type="submit"
                        class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-300 shadow-md">
                    Set PIN
                </button>
            </div>
        </form>
    </div>
</div>
{% endblock %}
"""

# templates/message.html
message_html_content = """
{% extends 'layout.html' %}

{% block title %}Message{% endblock %}

{% block content %}
<div class="text-center p-8 bg-white rounded-xl shadow-lg border border-gray-200">
    <h2 class="text-3xl font-extrabold text-gray-900 mb-4">Information</h2>
    <p class="text-lg text-gray-600">{{ message }}</p>
    <div class="mt-8">
        <a href="{{ url_for('login') }}" class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-full shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-300">
            Go to Login
        </a>
    </div>
</div>
{% endblock %}
"""

# Create the 'templates' directory and save the HTML content
os.makedirs('templates', exist_ok=True)

with open('templates/layout.html', 'w') as f:
    f.write(layout_html_content)

with open('templates/login.html', 'w') as f:
    f.write(login_html_content)

with open('templates/dashboard.html', 'w') as f:
    f.write(dashboard_html_content)

with open('templates/forgot_pin.html', 'w') as f:
    f.write(forgot_pin_html_content)

with open('templates/set_pin.html', 'w') as f:
    f.write(set_pin_html_content)

with open('templates/message.html', 'w') as f:
    f.write(message_html_content)

# To run this Flask app, save the above code as `app.py`
# and create a `templates` directory with the HTML files inside it.
# Then, from your terminal, navigate to the directory containing `app.py` and run:
# flask --app app run
# Or if you don't have flask in your path:
# python -m flask --app app run
# You can then access the application in your browser at http://127.0.0.1:5000/
#
# For initial testing, you can manually insert a user:
# 1. Run the app once to create database.db
# 2. Open `database.db` with a SQLite browser (e.g., DB Browser for SQLite)
# 3. Insert a user: INSERT INTO users (email, pin_hash) VALUES ('test@example.com', 'PBKDF2:sha256:260000$hN4pTq8xYvZwXc$b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3');
#    (The hash for '1234' is generated using `generate_password_hash('1234')`)
#    Alternatively, you can just go to /forgot_pin with a new email, and it will essentially "register" that email when you set the PIN.

# For demo purposes, let's create a dummy user upon first run if no users exist
@app.before_request
def check_for_users():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    if count == 0:
        print("No users found. Creating a default user: user@example.com with PIN 1234")
        # Hash '1234'
        hashed_pin = generate_password_hash('1234')
        try:
            db.execute(
                "INSERT INTO users (email, pin_hash) VALUES (?, ?)",
                ('user@example.com', hashed_pin)
            )
            db.commit()
            print("Default user created.")
        except sqlite3.IntegrityError:
            print("Default user already exists (likely due to previous run).")


if __name__ == '__main__':
    app.run(debug=True) # debug=True is for development only. Set to False for production.

