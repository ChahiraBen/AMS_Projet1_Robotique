from flask import Flask
from config import Config
from controllers.chatbot_controller import bp as chatbot_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(chatbot_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)