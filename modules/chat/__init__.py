from modules.chat.routes import chat_bp
from modules.chat.sockets import register_chat_sockets

def register_chat_module(app):
    app.register_blueprint(chat_bp)
    register_chat_sockets(app)
