# my_flask_app/__init__.py
import os
import pyodbc # Still needed for MS Access connection
from datetime import timedelta, datetime # Keep datetime for general use

from flask import Flask, g, session, flash, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash # Used for initial user creation

# Initialize SQLAlchemy instance globally
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # --- App Configuration ---
    app.secret_key = os.urandom(24) # Generates a random 24-byte key
    app.permanent_session_lifetime = timedelta(days=1)

    # MySQL Database Configuration for SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://rax:512@localhost/rcmain'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Avoids a warning

    # MS Access Database Path (for pyodbc)
    app.config['ACCESS_DB_PATH'] = r'C:\Users\Hp\My Drive\Z-DataFiles\rcPro.accdb'

    # Initialize SQLAlchemy with the app
    db.init_app(app)

    # --- MS Access Connection Management (pyodbc) ---
    def get_access_db_conn():
        """Establishes an MS Access database connection or returns the existing one."""
        if 'access_db_conn' not in g:
            conn_str = (
                r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
                f'DBQ={app.config["ACCESS_DB_PATH"]};'
            )
            try:
                g.access_db_conn = pyodbc.connect(conn_str)
            except pyodbc.Error as ex:
                sqlstate = ex.args[0]
                flash(f"Database connection error: {sqlstate}", 'danger')
                app.logger.error(f"Error connecting to MS Access DB: {ex}")
                # You might want to handle this more gracefully, e.g., redirect to an error page
                return None
        return g.access_db_conn

    @app.teardown_appcontext
    def close_access_db_conn(exception):
        """Closes the MS Access database connection."""
        conn = g.pop('access_db_conn', None)
        if conn is not None:
            conn.close()

    # --- Import Models (after db is initialized) ---
    # Import your models here so SQLAlchemy knows about them
    from . import models

    # --- Register Blueprints ---
    from .auth import auth_bp
    from .tasks import tasks_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)

    # --- Global Context Processor ---
    @app.context_processor
    def inject_current_year():
        """Injects the current year into all templates."""
        return {'current_year': datetime.now().year}

    # --- Helper for login_required (now accessible from blueprints) ---
    # This decorator needs to be imported by blueprints that use it.
    # It's defined here because it depends on Flask's session and url_for.
    def login_required(view):
        import functools
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            if 'user_id' not in session: # This 'user_id' comes from MS Access vemp table
                flash("Please log in to access this page.", 'info')
                return redirect(url_for('auth.login')) # Note: auth.login
            return view(**kwargs)
        return wrapped_view
    
    app.jinja_env.globals['login_required'] = login_required # Make decorator available globally

    # --- Initial User Creation (for MS Access 'vemp' table) ---
    # This runs when the app context is pushed, e.g., on first request or `app.app_context().push()`
    @app.before_request
    def check_for_users():
        # Only run this logic if it's the main request and not for static files, etc.
        if request.endpoint and not request.endpoint.startswith('static'):
            conn = get_access_db_conn()
            if conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT COUNT(*) FROM vemp")
                    count = cursor.fetchone()[0]
                    if count == 0:
                        app.logger.info("No users found in MS Access vemp table. Creating a default user.")
                        # Hash '1234'
                        hashed_pin = generate_password_hash('1234')
                        # Using 'code' instead of 'id' as per your original vemp table structure
                        # Note: MS Access doesn't typically have auto-incrementing 'code' like MySQL 'id'
                        # You might need to manage 'code' values manually or ensure it's auto-incremented
                        # in your Access DB schema if it's not already.
                        # For now, let's assume 'code' is handled by Access or insert dummy value if needed.
                        # If 'code' is auto-increment, you might not need to provide it.
                        # For simplicity, assuming a dummy `code` or that `vemp` handles it.
                        # If 'code' is PK and auto-increment, it's better to omit it from INSERT.
                        
                        # Assuming vemp has a PK (like 'id' or 'code') that's auto-generated
                        # or you explicitly define it if not.
                        # I'll modify this based on typical MS Access setup: if 'code' is PK, it's likely AutoNumber.
                        # If 'code' is not AutoNumber and is PK, you'd need to generate it, e.g., with UUID.
                        # For now, let's assume 'code' is implicitly handled if it's an AutoNumber field.
                        
                        try:
                            # Try to insert without 'code' if it's an AutoNumber field in Access
                            cursor.execute("INSERT INTO vemp (email, pin_hash, fullname) VALUES (?, ?, ?)",
                                           ('user@example.com', hashed_pin, 'Default User'))
                            conn.commit()
                            app.logger.info("Default user created in MS Access vemp table.")
                        except pyodbc.IntegrityError:
                            app.logger.warning("Default user 'user@example.com' already exists in vemp (likely due to previous run).")
                        except Exception as e:
                            app.logger.error(f"Error inserting default user into vemp: {e}")
                except pyodbc.ProgrammingError as pe:
                    app.logger.error(f"Error querying vemp table (table might not exist in Access DB): {pe}")
                except Exception as e:
                    app.logger.error(f"Unexpected error in check_for_users: {e}")
            else:
                app.logger.error("Could not get MS Access DB connection in before_request.")


    # --- Root route redirect ---
    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('tasks.dashboard')) # Redirect to blueprint dashboard
        return redirect(url_for('auth.login')) # Redirect to blueprint login

    return app