from .routes import services_bp


def register_services_module(app):
    app.register_blueprint(services_bp)
