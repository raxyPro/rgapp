from modules.social.routes import social_bp


def register_social_module(app):
    app.register_blueprint(social_bp)
