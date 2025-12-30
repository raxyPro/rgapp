from modules.chat.routes import chat_bp


def register_chat_module(app):
    app.register_blueprint(chat_bp)
