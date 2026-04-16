import tempfile
import os
import threading
import speech_recognition as sr
from flask import Blueprint, request, jsonify, session
from services.dialog_service import DialogService

bp = Blueprint("chatbot_bp", __name__)
dialog_service = DialogService()
recognizer = sr.Recognizer()

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


@bp.route("/transcribe", methods=["POST"])
def transcribe():
    """Reçoit un fichier audio WAV de Pepper et retourne le texte transcrit."""
    if "audio" not in request.files:
        return jsonify({"error": "Fichier audio manquant."}), 400

    audio_file = request.files["audio"]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
        audio_file.save(tmp_path)

    try:
        with sr.AudioFile(tmp_path) as source:
            audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data, language="fr-FR")
        return jsonify({"text": text})
    except sr.UnknownValueError:
        return jsonify({"text": "", "error": "Audio incompréhensible."})
    except sr.RequestError as e:
        return jsonify({"text": "", "error": "Erreur Google ASR : {}".format(e)}), 503
    finally:
        os.unlink(tmp_path)
