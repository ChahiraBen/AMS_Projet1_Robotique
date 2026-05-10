# -*- coding: utf-8 -*-


import qi
import argparse
import os
import time
import threading

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib2
    import json as _json

AUDIO_PATH = "/home/nao/input.wav"

_http_session = requests.Session() if HAS_REQUESTS else None


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def http_post_json(url, data):
    import json as _json_mod
    payload = _json_mod.dumps(data).encode("utf-8")
    if HAS_REQUESTS:
        r = _http_session.post(url, data=payload,
                               headers={"Content-Type": "application/json"}, timeout=15)
        return r.json()
    else:
        req = urllib2.Request(url, payload, {"Content-Type": "application/json"})
        resp = urllib2.urlopen(req, timeout=15)
        return _json.loads(resp.read().decode("utf-8"))


def http_post_audio(url, filepath):
    with open(filepath, "rb") as f:
        r = _http_session.post(url, files={"audio": ("audio.wav", f, "audio/wav")}, timeout=30)
        return r.json()


def http_get(url):
    if HAS_REQUESTS:
        r = requests.get(url, timeout=10)
        try:
            return r.json()
        except Exception:
            return {}
    else:
        try:
            resp = urllib2.urlopen(url, timeout=10)
            return _json.loads(resp.read().decode("utf-8"))
        except Exception:
            return {}


# ── Thread TTS ────────────────────────────────────────────────────────────────

def _clean_tts(text):
    """Nettoie le texte pour éviter que NAOqi interprète des caractères comme du markup."""
    # Guillemets typographiques → guillemets simples ou suppression
    text = text.replace(u"’", u"'")   # ' apostrophe courbe
    text = text.replace(u"‘", u"'")   # ' apostrophe ouvrante
    text = text.replace(u"“", u'"')   # " guillemet ouvrant
    text = text.replace(u"”", u'"')   # " guillemet fermant
    text = text.replace(u"«", u"")    # « guillemet français ouvrant
    text = text.replace(u"»", u"")    # » guillemet français fermant
    # Caractères spéciaux du markup NAOqi ALAnimatedSpeech
    text = text.replace(u"^", u"")
    text = text.replace(u"\\", u"")
    text = text.replace(u"\x00", u"")
    return text


class TTSPoller(threading.Thread):
    """Poll /speak toutes les secondes et fait parler Pepper."""

    def __init__(self, server_url, say_fn):
        super(TTSPoller, self).__init__()
        self.server_url  = server_url
        self.say_fn      = say_fn
        self.daemon      = True
        self._stop       = threading.Event()
        self.is_speaking = False

    def run(self):
        while not self._stop.is_set():
            if not self.is_speaking:
                try:
                    result = http_get("{}/speak".format(self.server_url))
                    text   = (result.get("text") or "").strip()
                    if text:
                        if len(text) > 400:
                            text = text[:397] + "..."
                        if not isinstance(text, type(u"")):
                            text = text.decode("utf-8", "replace")
                        text = _clean_tts(text)
                        self.is_speaking = True
                        try:
                            self.say_fn(text)
                        except Exception as e:
                            print("[TTS ERR] {}".format(e))
                        finally:
                            self.is_speaking = False
                except Exception as e:
                    print("[TTS POLL ERR] {}".format(e))
            time.sleep(1)

    def stop(self):
        self._stop.set()


# ── Thread MicController ──────────────────────────────────────────────────────

class MicController(threading.Thread):
    """Poll /mic/status, enregistre sur demande, transcrit et envoie au chatbot."""

    def __init__(self, server_url, recorder, tts_poller):
        super(MicController, self).__init__()
        self.server_url = server_url
        self.recorder   = recorder
        self.tts_poller = tts_poller
        self.daemon     = True
        self._stop      = threading.Event()

    def run(self):
        was_recording = False
        while not self._stop.is_set():
            try:
                if self.tts_poller.is_speaking:
                    time.sleep(0.5)
                    continue

                status    = http_get("{}/mic/status".format(self.server_url))
                recording = status.get("recording", False)

                if recording and not was_recording:
                    was_recording = True
                    try:
                        self.recorder.stopMicrophonesRecording()
                    except Exception:
                        pass
                    self.recorder.startMicrophonesRecording(AUDIO_PATH, "wav", 16000, [1, 0, 0, 0])
                    print("[MIC] Enregistrement démarré")

                elif not recording and was_recording:
                    was_recording = False
                    self.recorder.stopMicrophonesRecording()
                    time.sleep(0.3)
                    print("[MIC] Traitement audio...")
                    try:
                        try:
                            fsize = os.path.getsize(AUDIO_PATH)
                        except Exception:
                            fsize = 0
                        if fsize < 16000:
                            print("[MIC] Audio trop court ({} bytes), ignoré".format(fsize))
                            continue
                        result = http_post_audio("{}/transcribe".format(self.server_url), AUDIO_PATH)
                        text   = (result.get("text") or "").strip()
                        print("[MIC] Transcription : {}".format(
                            text.encode("utf-8", "replace") if isinstance(text, type(u"")) else text
                        ))
                        if text:
                            http_post_json("{}/chatbot".format(self.server_url),
                                          {"message": text, "source": "stt"})
                    except Exception as e:
                        print("[MIC ERR] {}".format(e))

            except Exception as e:
                print("[MIC ERR] {}".format(e))

            time.sleep(0.5)

    def stop(self):
        self._stop.set()


# ── Boucle principale ─────────────────────────────────────────────────────────

def run(server_url, pepper_ip="127.0.0.1", pepper_port=9559):

    app = qi.Application(
        ["PepperChatbot", "--qi-url", "tcp://{}:{}".format(pepper_ip, pepper_port)]
    )
    app.start()
    qi_session = app.session
    print("[OK] Connecté à NAOqi")

    def load_service(name, timeout=8):
        result = [None]
        def _load():
            try:
                result[0] = qi_session.service(name)
            except Exception as e:
                print("[WARN] {} non dispo : {}".format(name, e))
        t = threading.Thread(target=_load)
        t.daemon = True
        t.start()
        t.join(timeout)
        if result[0] is None:
            print("[WARN] {} timeout ou erreur".format(name))
        else:
            print("[OK]  {}".format(name))
        return result[0]

    print("[..] Chargement services...")
    tts       = load_service("ALTextToSpeech")
    animated  = load_service("ALAnimatedSpeech")
    motion    = load_service("ALMotion")
    awareness = load_service("ALBasicAwareness")
    tablet    = load_service("ALTabletService", timeout=5)

    if not tts or not animated or not motion:
        print("[ERR] Services essentiels manquants, arrêt.")
        app.stop()
        return

    tts.setLanguage("French")
    motion.wakeUp()
    print("[OK] wakeUp")

    if tablet:
        tablet.showWebview("{}/".format(server_url))
        print("[OK] Tablette : {}".format(server_url))

    if awareness:
        awareness.setEngagementMode("FullyEngaged")
        awareness.startAwareness()
        print("[OK] Awareness")

    animated.say("Bonjour ! Je suis votre assistant d accueil.")

    tts_poller = TTSPoller(server_url, tts.say)
    tts_poller.start()
    print("[OK] Thread TTS démarré")

    print("[..] Chargement ALAudioRecorder...")
    recorder = load_service("ALAudioRecorder")

    mic_ctrl = None
    if recorder:
        mic_ctrl = MicController(server_url, recorder, tts_poller)
        mic_ctrl.start()
        print("[OK] Thread MicController démarré")
    else:
        print("[WARN] ALAudioRecorder indisponible — bouton micro désactivé")

    print("[OK] En attente — Ctrl+C pour arrêter")
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n[..] Arrêt.")
    finally:
        tts_poller.stop()
        if mic_ctrl:
            mic_ctrl.stop()
        motion.rest()
        app.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server",      default="http://127.0.0.1:5000")
    parser.add_argument("--pepper-ip",   default="127.0.0.1")
    parser.add_argument("--pepper-port", default=9559, type=int)
    args = parser.parse_args()

    # Corriger http:/ → http:// si j'ai oublié un slash
    server = args.server
    if server.startswith("http:/") and not server.startswith("http://"):
        server = "http://" + server[6:]
    elif server.startswith("https:/") and not server.startswith("https://"):
        server = "https://" + server[7:]
    if server != args.server:
        print("[WARN] URL corrigée : {} → {}".format(args.server, server))

    run(server, args.pepper_ip, args.pepper_port)
