#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Serveur ASR Google - base sur le cours de F. Lefevre (Univ. Avignon, 2020).
Lancer : python googleSR_server.py --port 5001
Pepper envoie : POST /google { "data": "<base64 frames>", "params": "<base64 tuple params>" }
Reponse      : { "sentence": "texte reconnu" }
"""

import argparse
import base64
import os
import tempfile
import wave
from ast import literal_eval

import speech_recognition as sr
from flask import Flask, request, jsonify

app = Flask(__name__)
recognizer = sr.Recognizer()


def speechRecognition(data, params):
    data   = base64.b64decode(data)
    params = literal_eval(base64.b64decode(params).decode("utf-8"))

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        wf = wave.open(tmp.name, "w")
        wf.setparams(params)
        wf.writeframes(data)
        wf.close()

        with sr.AudioFile(tmp.name) as source:
            audio = recognizer.record(source)

        return recognizer.recognize_google(audio, language="fr-FR")
    except sr.UnknownValueError:
        return None
    except Exception as e:
        print("[ASR] Erreur : {}".format(e))
        return None
    finally:
        os.unlink(tmp.name)


@app.route("/google", methods=["POST"])
def transcribe():
    payload = request.get_json(force=True)
    if not payload or "data" not in payload or "params" not in payload:
        return jsonify({"sentence": None, "error": "Champs data et params requis"}), 400
    sentence = speechRecognition(payload["data"], payload["params"])
    print("[ASR] Transcription : {}".format(sentence))
    return jsonify({"sentence": sentence})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=5001, type=int)
    args = parser.parse_args()
    print("[ASR] Serveur demarre sur {}:{}".format(args.host, args.port))
    app.run(host=args.host, port=args.port, debug=False)
