import threading
import tempfile
import os
from flask import Blueprint, request, jsonify, session
from services.dialog_service import DialogService

import speech_recognition as sr
_recognizer = sr.Recognizer()

bp = Blueprint("chatbot_bp", __name__)
dialog_service = DialogService()

_chat_queue = []
_chat_lock  = threading.Lock()

_speak_queue = []
_speak_lock  = threading.Lock()

_mic_recording = False
_mic_lock      = threading.Lock()


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
    source  = payload.get("source", "tablet")

    if not message:
        return jsonify({"error": "Veuillez saisir un message."}), 400

    result = dialog_service.handle_message(message, session)
    response_text = result.get("response", "")

    if source == "stt":
        _push_chat("user", message)
        if response_text:
            _push_chat("bot", response_text)
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


@bp.route("/reset", methods=["POST"])
def reset():
    session.clear()
    return jsonify({"status": "ok"})


@bp.route("/speak", methods=["GET"])
def speak():
    with _speak_lock:
        if _speak_queue:
            text = _speak_queue.pop(0)
            return jsonify({"text": text})
    return jsonify({"text": ""})


@bp.route("/updates", methods=["GET"])
def updates():
    with _chat_lock:
        msgs = list(_chat_queue)
        del _chat_queue[:]
    return jsonify({"messages": msgs})
