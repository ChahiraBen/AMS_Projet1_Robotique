# -*- coding: utf-8 -*-
"""
Script à exécuter DIRECTEMENT SUR LE ROBOT Pepper (Python 2.7).
Déploiement : copier ce fichier sur Pepper via SSH/SCP, puis lancer.

Depuis ton PC :
  scp robot_script.py nao@IP_PEPPER:/home/nao/chatbot.py
  ssh nao@IP_PEPPER "python /home/nao/chatbot.py --server http://IP_TON_PC:5000"
"""

import qi
import argparse
import os
import sys

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib2
    import json as _json

RECORD_SECONDS = 5
AUDIO_PATH = "/home/nao/input.wav"


# ── HTTP helpers (compatible Python 2.7) ─────────────────────────────────────
def http_post_json(url, data):
    if HAS_REQUESTS:
        r = requests.post(url, json=data, timeout=15)
        return r.json()
    else:
        payload = _json.dumps(data).encode("utf-8")
        req = urllib2.Request(url, payload, {"Content-Type": "application/json"})
        resp = urllib2.urlopen(req, timeout=15)
        return _json.loads(resp.read().decode("utf-8"))


def http_post_file(url, filepath):
    if HAS_REQUESTS:
        with open(filepath, "rb") as f:
            r = requests.post(url, files={"audio": ("voice.wav", f, "audio/wav")}, timeout=20)
        return r.json()
    else:
        # multipart manuel Python 2
        import mimetools
        import mimetypes
        boundary = mimetools.choose_boundary()
        with open(filepath, "rb") as f:
            audio_bytes = f.read()
        body = (
            "--" + boundary + "\r\n"
            "Content-Disposition: form-data; name=\"audio\"; filename=\"voice.wav\"\r\n"
            "Content-Type: audio/wav\r\n\r\n"
        ).encode("utf-8") + audio_bytes + ("\r\n--" + boundary + "--\r\n").encode("utf-8")
        req = urllib2.Request(url, body, {
            "Content-Type": "multipart/form-data; boundary=" + boundary,
            "Content-Length": str(len(body)),
        })
        resp = urllib2.urlopen(req, timeout=20)
        return _json.loads(resp.read().decode("utf-8"))


# ── Boucle principale ─────────────────────────────────────────────────────────
def run(server_url, pepper_ip="127.0.0.1", pepper_port=9559):

    # 1. Connexion à NAOqi (en local sur le robot → 127.0.0.1)
    app = qi.Application(
        ["PepperChatbot", "--qi-url", "tcp://{}:{}".format(pepper_ip, pepper_port)]
    )
    app.start()
    session = app.session
    print("[OK] Connecté à NAOqi")

    # 2. Services
    print("[..] Chargement services...")
    tts       = session.service("ALTextToSpeech")
    animated  = session.service("ALAnimatedSpeech")
    tablet    = session.service("ALTabletService")
    awareness = session.service("ALBasicAwareness")
    motion    = session.service("ALMotion")
    print("[OK] Services chargés")

    # 3. Config
    tts.setLanguage("French")
    motion.wakeUp()
    print("[OK] wakeUp fait")

    # 4. Tablette → afficher l'interface Flask
    tablet.showWebview("{}/".format(server_url))
    print("[OK] Interface web sur la tablette : {}".format(server_url))

    # 5. Conscience basique
    awareness.setEngagementMode("FullyEngaged")
    awareness.startAwareness()

    # 6. Salutation
    animated.say("Bonjour ! Je suis votre assistant d'accueil. Utilisez la tablette pour me parler.")
    print("[OK] En attente — Ctrl+C pour arrêter")

    try:
        app.run()  # garde le process vivant
    except KeyboardInterrupt:
        print("\n[..] Arrêt.")

    motion.rest()
    app.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server",      default="http://127.0.0.1:5000", help="URL du backend Flask")
    parser.add_argument("--pepper-ip",   default="127.0.0.1",             help="IP NAOqi (127.0.0.1 si sur le robot)")
    parser.add_argument("--pepper-port", default=9559, type=int)
    args = parser.parse_args()
    run(args.server, args.pepper_ip, args.pepper_port)
