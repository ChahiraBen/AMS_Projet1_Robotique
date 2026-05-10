from flask import Flask, render_template
from config import Config
from controllers.chatbot_controller import bp as chatbot_bp
from controllers.conversations_controller import bp as conv_bp
from repositories.conv_repo import recover_orphaned_conversations


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    recover_orphaned_conversations()

    app.register_blueprint(chatbot_bp)
    app.register_blueprint(conv_bp)

    @app.route("/")
    def welcome():
        return render_template("welcome.html")

    @app.route("/chat")
    def index():
        return render_template("index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
