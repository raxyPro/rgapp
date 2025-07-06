import os

# Persist session for a day
from datetime import datetime, timedelta
from flask import Flask, session, flash, redirect, url_for
from flask_mail import Mail
from werkzeug.security import generate_password_hash
from .models import db, Vemp
from .routes.auth_routes import auth_bp
from .routes.task_routes import task_bp
from .routes.prof_routes import prof_bp

#from .admin_routes import admin_bp

# to test the chat app


def create_app():
    app = Flask(__name__)
    #app.secret_key = os.urandom(24).hex()
    app.secret_key = '4c912ab54d99be8e1f3848f3d61f4f6d9aef827c64a8cddbbf96a80a3545d911'
    app.permanent_session_lifetime = timedelta(days=1)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://rax:512@localhost/rcmain'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False  # Enable SQL query logging for debugging



    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)

    db.init_app(app)

    @app.teardown_appcontext
    def teardown_db(_):
        db.session.remove()

    def login_required(view):
        import functools
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            if 'user_code' not in session:
                flash("Please log in to access this page.", 'info')
                return redirect(url_for('login'))
            return view(**kwargs)
        return wrapped_view

    @app.context_processor
    def inject_current_year():
        return {'current_year': datetime.now().year}

    @app.before_request
    def make_session_permanent():
        session.permanent = True
    def check_for_users():
        if Vemp.query.count() == 0:
            print("No users found. Creating a default user: user@example.com with PIN 1234")
            hashed_pin = generate_password_hash('1234')
            default_user = Vemp(email='user@example.com', pin_hash=hashed_pin)
            db.session.add(default_user)
            db.session.commit()
            print("Default user created.")

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(prof_bp)
    #app.register_blueprint(admin_bp)
    
    


    return app
