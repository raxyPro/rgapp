from modules.profiles.routes import profiles_bp, profileviewer_bp, vcardviewer_bp


def register_profiles_module(app):
    app.register_blueprint(profiles_bp)
    app.register_blueprint(profileviewer_bp)
    app.register_blueprint(vcardviewer_bp)
