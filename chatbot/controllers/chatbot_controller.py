import threading
import tempfile
import os
from flask import Blueprint, request, jsonify, session
from services.dialog_service import DialogService

import speech_recognition as sr
_recognizer = sr.Recognizer()

bp = Blueprint("chatbot_bp", __name__)
dialog_service = DialogService()

# File de messages pour la tablette (messages venant du STT)
_chat_queue = []
_chat_lock  = threading.Lock()

# File TTS pour Pepper
_speak_queue = []
_speak_lock  = threading.Lock()

# État du micro robot (déclenché depuis la tablette)
_mic_recording    = False
_mic_lock         = threading.Lock()

# Transcription en attente d'affichage sur la tablette
_pending_transcript = ""
_pending_lock       = threading.Lock()


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

    response_text = result.get("response", "")

    if source == "stt":
        # Depuis le micro du robot → afficher sur tablette + Pepper parle
        _push_chat("user", message)
        if response_text:
            _push_chat("bot", response_text)
            _push_speak(response_text)
    elif source == "mic":
        # Depuis le bouton micro de la tablette → tablette affiche déjà, Pepper parle
        if response_text:
            _push_speak(response_text)

    return jsonify(result)


@bp.route("/transcribe", methods=["POST"])
def transcribe():
    audio = request.files.get("audio")
    if not audio:
        return jsonify({"text": ""}), 400

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
        audio.save(tmp_path)

    text = ""
    try:
        with sr.AudioFile(tmp_path) as source:
            audio_data = _recognizer.record(source)
        text = _recognizer.recognize_google(audio_data, language="fr-FR")
        print("[STT] {}".format(text))
    except sr.UnknownValueError:
        print("[STT] Parole non reconnue")
    except Exception as e:
        print("[STT ERR] {}".format(e))
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    return jsonify({"text": text})


@bp.route("/mic/start", methods=["POST"])
def mic_start():
    global _mic_recording
    with _mic_lock:
        _mic_recording = True
    return jsonify({"status": "started"})


@bp.route("/mic/stop", methods=["POST"])
def mic_stop():
    global _mic_recording
    with _mic_lock:
        _mic_recording = False
    return jsonify({"status": "stopped"})


@bp.route("/mic/status", methods=["GET"])
def mic_status():
    with _mic_lock:
        return jsonify({"recording": _mic_recording})


@bp.route("/mic/result", methods=["POST"])
def mic_result_post():
    global _pending_transcript
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    with _pending_lock:
        _pending_transcript = text
    return jsonify({"status": "ok"})


@bp.route("/mic/result", methods=["GET"])
def mic_result_get():
    global _pending_transcript
    with _pending_lock:
        text = _pending_transcript
        _pending_transcript = ""
    return jsonify({"text": text})


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


