from flask import Flask, render_template, session
from config import Config
from controllers.chatbot_controller import bp as chatbot_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    @app.before_request
    def make_session_permanent():
        session.permanent = True

    app.register_blueprint(chatbot_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
