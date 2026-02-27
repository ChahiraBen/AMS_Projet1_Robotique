from flask import Blueprint, request, jsonify, session
from services.dialog_service import DialogService

bp = Blueprint("chatbot_bp", __name__)
dialog_service = DialogService()

@bp.route("/chatbot", methods=["POST"])
def chatbot():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()

    if not message:
        return jsonify({"error": "Veuillez saisir un message."}), 400

    result = dialog_service.handle_message(message, session)
    return jsonify(result)