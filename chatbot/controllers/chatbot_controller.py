import threading
from flask import Blueprint, request, jsonify, session
from services.dialog_service import DialogService

bp = Blueprint("chatbot_bp", __name__)
dialog_service = DialogService()

# File de messages pour la tablette (messages venant du STT)
_chat_queue = []
_chat_lock  = threading.Lock()

# File TTS pour Pepper
_speak_queue = []
_speak_lock  = threading.Lock()


def _push_chat(role, text):
    with _chat_lock:
        _chat_queue.append({"role": role, "text": text})


def _push_speak(text):
    with _speak_lock:
        _speak_queue.append(text)


@bp.route("/chatbot", methods=["POST"])
def chatbot():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    source  = payload.get("source", "tablet")  # "stt" ou "tablet"

    if not message:
        return jsonify({"error": "Veuillez saisir un message."}), 400

    result = dialog_service.handle_message(message, session)

    # Si le message vient du STT, pousser dans la queue tablette + queue TTS
    if source == "stt":
        response_text = result.get("response", "")
        _push_chat("user", message)
        if response_text:
            _push_chat("bot", response_text)
            _push_speak(response_text)

    return jsonify(result)


@bp.route("/reset", methods=["POST"])
def reset():
    session.clear()
    return jsonify({"status": "ok"})


@bp.route("/speak", methods=["GET"])
def speak():
    """Pepper poll cet endpoint pour récupérer le prochain texte à dire."""
    with _speak_lock:
        if _speak_queue:
            text = _speak_queue.pop(0)
            return jsonify({"text": text})
    return jsonify({"text": ""})


@bp.route("/updates", methods=["GET"])
def updates():
    """La tablette poll cet endpoint pour afficher les messages venant du STT."""
    with _chat_lock:
        messages = list(_chat_queue)
        del _chat_queue[:]
    return jsonify({"messages": messages})


