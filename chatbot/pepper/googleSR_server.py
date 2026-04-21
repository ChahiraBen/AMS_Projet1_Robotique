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
import wave
from ast import literal_eval

import speech_recognition as sr
from flask import Flask, request, jsonify

app = Flask(__name__)


def speechRecognition(data, params):
    r = sr.Recognizer()

    audioFileName = "test.wav"
    data = base64.b64decode(data)
    params = base64.b64decode(params)
    params = literal_eval(params.decode("utf-8"))

    wave_write = wave.open(audioFileName, "w")
    wave_write.setparams(params)
    wave_write.writeframes(data)
    wave_write.close()

    with sr.AudioFile(audioFileName) as source:
        audioFile = r.record(source)

    try:
        text = r.recognize_google(audioFile, language="fr-FR")
        return text
    except Exception as e:
        print(e)
        return None


@app.route("/google", methods=["POST"])
def transcribe():
    req_data = request.get_json(force=True)
    result = speechRecognition(req_data["data"], req_data["params"])
    print(result)
    return jsonify({"sentence": result})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=5001, type=int)
    args = parser.parse_args()
    print("[ASR] Serveur demarre sur {}:{}".format(args.host, args.port))
    app.run(host=args.host, port=args.port, debug=False)
