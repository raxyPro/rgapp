from flask import Flask
from config import Config
from extensions import db, login_manager

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from routes_home import home_bp
    from routes_auth import auth_bp
    from routes_admin import admin_bp
    from routes_user import user_bp


    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)

    #debug
    #for r in app.url_map.iter_rules():
    #    print(r)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
