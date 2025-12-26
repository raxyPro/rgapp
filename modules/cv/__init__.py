from modules.cv.routes import cv_bp, cvviewer_bp


def register_cv_module(app):
    app.register_blueprint(cv_bp)
    app.register_blueprint(cvviewer_bp)
