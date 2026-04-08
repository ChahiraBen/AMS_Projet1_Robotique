import tempfile
import os
import speech_recognition as sr
from flask import Blueprint, request, jsonify, session
from services.dialog_service import DialogService

bp = Blueprint("chatbot_bp", __name__)
dialog_service = DialogService()
recognizer = sr.Recognizer()


@bp.route("/chatbot", methods=["POST"])
def chatbot():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()

    if not message:
        return jsonify({"error": "Veuillez saisir un message."}), 400

    result = dialog_service.handle_message(message, session)
    return jsonify(result)


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
        return jsonify({"text": "", "error": f"Erreur Google ASR : {e}"}), 503
    finally:
        os.unlink(tmp_path)
