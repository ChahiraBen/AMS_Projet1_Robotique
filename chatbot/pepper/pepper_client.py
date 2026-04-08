"""
Client Pepper – connexion via qi (sans Choreographe).

Prérequis :
  pip install qi requests

Usage :
  python pepper_client.py --pepper-ip 192.168.X.X --server-url http://192.168.X.X:5000
"""

import argparse
import time
import requests
import qi


# ── Configuration par défaut ─────────────────────────────────────────────────
DEFAULT_PEPPER_IP  = "192.168.13.213"   # ←   l'IP de  Pepper
DEFAULT_PEPPER_PORT = 9559
DEFAULT_SERVER_URL = "http://10.126.6.112:5000"   # ← IP de  PC sur le réseau WiFi

RECORD_SECONDS = 5          # durée d'écoute par tour
AUDIO_TMP_PATH = "/tmp/pepper_input.wav"   # chemin sur le robot


# ── Initialisation des services NAOqi ─────────────────────────────────────────
def get_services(session):
    tts      = session.service("ALTextToSpeech")
    animated = session.service("ALAnimatedSpeech")
    recorder = session.service("ALAudioRecorder")
    tablet   = session.service("ALTabletService")
    awareness = session.service("ALBasicAwareness")
    motion   = session.service("ALMotion")
    return tts, animated, recorder, tablet, awareness, motion


# ── Enregistrement audio depuis les micros de Pepper ─────────────────────────
def listen(recorder, seconds=RECORD_SECONDS):
    """Enregistre l'audio du micro frontal de Pepper (WAV 16 kHz)."""
    # channels : [front, rear, left, right]  – 1 = activer le micro frontal
    recorder.startMicrophonesRecording(AUDIO_TMP_PATH, "wav", 16000, [1, 0, 0, 0])
    time.sleep(seconds)
    recorder.stopMicrophonesRecording()


# ── Transcription via le backend Flask ───────────────────────────────────────
def transcribe(server_url, pepper_session):
    """Lit le fichier WAV sur le robot et l'envoie au serveur pour transcription."""
    # Lire les bytes du fichier directement via qi (le fichier est sur le robot)
    try:
        memory = pepper_session.service("ALMemory")
        # Alternative : utiliser ftplib/paramiko pour récupérer le fichier
        # Ici on suppose que le robot et le serveur sont sur le même réseau
        # et on lit directement depuis le système de fichiers du robot via SSH,
        # OU on utilise l'endpoint /transcribe_raw avec un chemin.
        pass
    except Exception:
        pass

    # Approche la plus simple : ouvrir le fichier WAV via le module filesystem qi
    import paramiko  # pip install paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # Mot de passe par défaut Pepper : vide ou "pepper"
    ssh.connect(DEFAULT_PEPPER_IP, username="nao", password="")
    sftp = ssh.open_sftp()
    with sftp.open(AUDIO_TMP_PATH, "rb") as f:
        audio_bytes = f.read()
    sftp.close()
    ssh.close()

    resp = requests.post(
        f"{server_url}/transcribe",
        files={"audio": ("voice.wav", audio_bytes, "audio/wav")},
        timeout=15,
    )
    return resp.json().get("text", "")


# ── Appel au chatbot ──────────────────────────────────────────────────────────
def ask_chatbot(server_url, message, session_cookies=None):
    resp = requests.post(
        f"{server_url}/chatbot",
        json={"message": message},
        cookies=session_cookies,
        timeout=15,
    )
    data = resp.json()
    return data.get("response", "Je n'ai pas compris."), resp.cookies


# ── Boucle principale ─────────────────────────────────────────────────────────
def run(pepper_ip, pepper_port, server_url):
    # 1. Connexion à Pepper
    app = qi.Application(
        ["PepperChatbot", "--qi-url", f"tcp://{pepper_ip}:{pepper_port}"]
    )
    app.start()
    session = app.session
    print(f"[OK] Connecté à Pepper ({pepper_ip}:{pepper_port})")

    tts, animated, recorder, tablet, awareness, motion = get_services(session)

    # 2. Configuration langue
    tts.setLanguage("French")

    # 3. Afficher l'interface web sur la tablette
    tablet.showWebview(f"{server_url}/")
    print(f"[OK] Interface affichée sur la tablette : {server_url}/")

    # 4. Démarrer la conscience basique (détection de personnes)
    awareness.setEngagementMode("FullyEngaged")
    awareness.startAwareness()

    # 5. Posture initiale
    motion.wakeUp()

    # 6. Salutation
    greeting = "Bonjour ! Je suis votre assistant d'accueil. Comment puis-je vous aider ?"
    animated.say(greeting)

    session_cookies = None
    print("[..] Démarrage de la boucle d'interaction. Ctrl+C pour arrêter.")

    while True:
        try:
            print("[..] Écoute en cours...")
            listen(recorder, seconds=RECORD_SECONDS)

            print("[..] Transcription...")
            text = transcribe(server_url, session)

            if not text:
                animated.say("Je n'ai pas bien entendu. Pouvez-vous répéter ?")
                continue

            print(f"[USER] {text}")

            response, session_cookies = ask_chatbot(server_url, text, session_cookies)
            print(f"[PEPPER] {response}")

            animated.say(response)

            # Fin de conversation
            if any(w in text.lower() for w in ("au revoir", "bye", "merci au revoir")):
                animated.say("Au revoir et bonne journée !")
                break

        except KeyboardInterrupt:
            print("\n[..] Arrêt demandé.")
            break
        except Exception as e:
            print(f"[ERR] {e}")
            tts.say("Une erreur est survenue. Je réessaie.")
            time.sleep(2)

    motion.rest()
    app.stop()


# ── Point d'entrée ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pepper-ip",   default=DEFAULT_PEPPER_IP)
    parser.add_argument("--pepper-port", default=DEFAULT_PEPPER_PORT, type=int)
    parser.add_argument("--server-url",  default=DEFAULT_SERVER_URL)
    args = parser.parse_args()

    run(args.pepper_ip, args.pepper_port, args.server_url)
