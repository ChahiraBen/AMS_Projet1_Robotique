import threading
import tempfile
import os
from flask import Blueprint, request, jsonify, session
from openai import OpenAI
from config import Config
from services.dialog_service import DialogService
from repositories.conv_repo import ConversationRepository

bp = Blueprint("chatbot_bp", __name__)
dialog_service = DialogService()
_conv_repo = ConversationRepository()
_whisper = OpenAI(api_key=Config.OPENAI_API_KEY)

_robot_conv_id      = None
_robot_conv_lock    = threading.Lock()


def _get_robot_conv_id():
    global _robot_conv_id
    with _robot_conv_lock:
        if _robot_conv_id is None:
            _robot_conv_id = _conv_repo.create_robot()
        return _robot_conv_id

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

    conversation_id = payload.get("conversation_id", "")
    if not conversation_id:
        if source == "stt":
            conversation_id = _get_robot_conv_id()
        else:
            return jsonify({"error": "conversation_id manquant"}), 400

    result = dialog_service.handle_message(message, conversation_id)
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
        # Ignorer les enregistrements trop courts (< ~0.5s à 16kHz mono 16-bit)
        file_size = os.path.getsize(tmp_path)
        if file_size < 16000:
            print("[STT] Audio trop court ({} bytes), ignoré".format(file_size))
            return jsonify({"text": ""})

        with open(tmp_path, "rb") as f:
            resp = _whisper.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="fr",
                temperature=0,
                prompt="Hôpital. Patient demande localisation service, médecin, horaire, rendez-vous.",
                response_format="verbose_json",
            )

        # Filtre anti-hallucination : no_speech_prob élevé = silence ou bruit
        segments = getattr(resp, "segments", None) or []
        if segments:
            avg_nsp = sum(getattr(s, "no_speech_prob", 0) for s in segments) / len(segments)
            if avg_nsp > 0.65:
                print("[STT] Silence/bruit détecté (no_speech_prob={:.2f}), ignoré".format(avg_nsp))
                return jsonify({"text": ""})

        text = (resp.text or "").strip()
        if len(text) < 3:
            text = ""

        print("[STT]", text)
    except Exception as e:
        print("[STT ERR]", e)
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


@bp.route("/speak/push", methods=["POST"])
def speak_push():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    if text:
        _push_speak(text)
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
