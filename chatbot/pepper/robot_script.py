# -*- coding: utf-8 -*-
"""
Script à exécuter DIRECTEMENT SUR LE ROBOT Pepper (Python 2.7).
Déploiement : copier ce fichier sur Pepper via SSH/SCP, puis lancer.

Depuis ton PC :
  scp robot_script.py nao@IP_PEPPER:/home/nao/chatbot.py
  ssh nao@IP_PEPPER "python /home/nao/chatbot.py --server http://IP_TON_PC:5000 --stt"
"""

import qi
import argparse
import base64
import time
import threading
import struct
import wave

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib2
    import json as _json

RECORD_SECONDS      = 6
AUDIO_PATH          = "/home/nao/input.wav"
AMPLITUDE_THRESHOLD = 500  # amplitude moyenne minimum pour détecter la vraie parole


# ── HTTP helpers (compatible Python 2.7) ─────────────────────────────────────

_http_session = requests.Session() if HAS_REQUESTS else None


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


def wav_to_base64(filepath):
    """Lit un WAV et retourne (b64_frames, b64_params) — compatible Python 2.7."""
    wf = wave.open(filepath, "r")
    try:
        params = wf.getparams()
        frames = wf.readframes(wf.getnframes())
    finally:
        wf.close()
    b64_data   = base64.b64encode(frames).decode("utf-8")
    b64_params = base64.b64encode(str(tuple(params)).encode("utf-8")).decode("utf-8")
    return b64_data, b64_params


def http_post_asr(asr_url, filepath):
    """Envoie l'audio WAV encode en base64 au serveur ASR (approche prof Lefevre)."""
    b64_data, b64_params = wav_to_base64(filepath)
    return http_post_json(asr_url, {"data": b64_data, "params": b64_params})


# ── Détection de parole par amplitude ────────────────────────────────────────

def has_speech(filepath):
    """Retourne True si le fichier WAV contient de la vraie parole (pas du silence)."""
    try:
        wf = wave.open(filepath, "r")
        try:
            n_frames = wf.getnframes()
            if n_frames == 0:
                return False
            raw = wf.readframes(n_frames)
        finally:
            wf.close()
        n_samples = len(raw) // 2
        if n_samples == 0:
            return False
        samples = struct.unpack("<" + "h" * n_samples, raw)
        avg = sum(abs(s) for s in samples) / n_samples
        print("[STT] Amplitude moyenne : {:.0f}".format(avg))
        return avg > AMPLITUDE_THRESHOLD
    except Exception as e:
        print("[STT] Erreur analyse audio : {}".format(e))
        return True  # en cas d'erreur, envoyer quand même


# ── HTTP GET ─────────────────────────────────────────────────────────────────

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

class TTSPoller(threading.Thread):
    """Poll /speak toutes les secondes et fait parler Pepper."""

    def __init__(self, server_url, say_fn):
        super(TTSPoller, self).__init__()
        self.server_url = server_url
        self.say_fn     = say_fn   # animated.say
        self.daemon     = True
        self._stop      = threading.Event()
        self.is_speaking = False

    def run(self):
        while not self._stop.is_set():
            if not self.is_speaking:
                try:
                    result = http_get("{}/speak".format(self.server_url))
                    text   = (result.get("text") or "").strip()
                    if text:
                        # Tronquer à 150 caractères pour animated.say
                        if len(text) > 150:
                            text = text[:147] + "..."
                        try:
                            encoded = text.encode("utf-8") if isinstance(text, type(u"")) else text
                        except Exception:
                            encoded = text
                        self.is_speaking = True
                        try:
                            self.say_fn(encoded)
                        except Exception as e:
                            print("[TTS ERR] {}".format(e))
                        finally:
                            self.is_speaking = False
                except Exception as e:
                    print("[TTS POLL ERR] {}".format(e))
            time.sleep(1)

    def stop(self):
        self._stop.set()


# ── Envoi fichier audio WAV au backend ───────────────────────────────────────

def http_post_audio(url, filepath):
    with open(filepath, "rb") as f:
        r = _http_session.post(url, files={"audio": ("audio.wav", f, "audio/wav")}, timeout=30)
        return r.json()


# ── Thread MicController (bouton micro tablette) ──────────────────────────────

class MicController(threading.Thread):
    """Poll /mic/status et enregistre quand la tablette active le micro."""

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
                        result = http_post_audio("{}/transcribe".format(self.server_url), AUDIO_PATH)
                        text   = (result.get("text") or "").strip()
                        print("[MIC] Transcription : {}".format(
                            text.encode("utf-8", "replace") if isinstance(text, type(u"")) else text
                        ))
                        if text:
                            http_post_json("{}/chatbot".format(self.server_url),
                                          {"message": text, "source": "stt"})
                    except Exception as e:
                        print("[MIC ERR] Transcription : {}".format(e))

            except Exception as e:
                print("[MIC ERR] {}".format(e))

            time.sleep(0.5)

    def stop(self):
        self._stop.set()


# ── Thread STT ────────────────────────────────────────────────────────────────

class STTLoop(threading.Thread):
    """Enregistre le micro de Pepper, transcrit via ASR server, envoie à /chatbot."""

    def __init__(self, server_url, asr_url, recorder, tts_service, tts_poller):
        super(STTLoop, self).__init__()
        self.server_url  = server_url
        self.asr_url     = asr_url
        self.recorder    = recorder
        self.tts         = tts_service
        self.tts_poller  = tts_poller
        self.daemon      = True
        self._stop       = threading.Event()

    def run(self):
        # Dire "j'écoute" une seule fois au démarrage
        try:
            self.tts.say("J ecoute.")
            time.sleep(0.3)
        except Exception:
            pass

        while not self._stop.is_set():
            try:
                # Attendre que Pepper finisse de parler
                if self.tts_poller.is_speaking:
                    time.sleep(0.5)
                    continue

                # Arrêter un éventuel enregistrement en cours
                try:
                    self.recorder.stopMicrophonesRecording()
                except Exception:
                    pass

                print("[STT] Enregistrement {} secondes...".format(RECORD_SECONDS))
                self.recorder.startMicrophonesRecording(AUDIO_PATH, "wav", 16000, [1, 0, 0, 0])
                time.sleep(RECORD_SECONDS)
                self.recorder.stopMicrophonesRecording()
                time.sleep(0.5)

                # Filtrer le silence
                if not has_speech(AUDIO_PATH):
                    print("[STT] Silence, ignoré.")
                    continue  # reboucle sans rien dire

                # Transcrire via le serveur ASR (approche prof Lefevre)
                print("[STT] Envoi au serveur ASR...")
                result = http_post_asr("{}/google".format(self.asr_url), AUDIO_PATH)
                text = (result.get("sentence") or "").strip()
                print("[STT] Transcription : {}".format(
                    text.encode("utf-8", "replace") if isinstance(text, type(u"")) else text
                ))

                if not text:
                    print("[STT] Texte vide, ignoré.")
                    continue

                # Envoyer au chatbot
                try:
                    msg = text.encode("utf-8") if isinstance(text, type(u"")) else text
                except Exception:
                    msg = text
                chatbot_result = http_post_json("{}/chatbot".format(self.server_url), {"message": msg, "source": "stt"})
                response = (chatbot_result.get("response") or "").strip()
                print("[CHATBOT] {}".format(
                    response.encode("utf-8", "replace") if isinstance(response, type(u"")) else response
                ))

                # Prêt pour la prochaine question
                time.sleep(0.5)
                try:
                    self.tts.say("J ecoute.")
                    time.sleep(0.3)
                except Exception:
                    pass

            except Exception as e:
                print("[STT ERR] {}".format(e))
                time.sleep(2)

    def stop(self):
        self._stop.set()


# ── Boucle principale ─────────────────────────────────────────────────────────

def run(server_url, asr_url, pepper_ip="127.0.0.1", pepper_port=9559, enable_stt=False):

    app = qi.Application(
        ["PepperChatbot", "--qi-url", "tcp://{}:{}".format(pepper_ip, pepper_port)]
    )
    app.start()
    qi_session = app.session
    print("[OK] Connecté à NAOqi")

    # Chargement des services avec timeout individuel
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
    tts      = load_service("ALTextToSpeech")
    animated = load_service("ALAnimatedSpeech")
    motion   = load_service("ALMotion")
    awareness = load_service("ALBasicAwareness")
    tablet   = load_service("ALTabletService", timeout=5)

    if not tts or not animated or not motion:
        print("[ERR] Services essentiels manquants, arrêt.")
        app.stop()
        return

    print("[OK] Services chargés")

    print("[..] setLanguage...")
    tts.setLanguage("French")
    print("[OK] setLanguage")

    print("[..] wakeUp...")
    motion.wakeUp()
    print("[OK] wakeUp")

    if tablet:
        print("[..] showWebview...")
        tablet.showWebview("{}/".format(server_url))
        print("[OK] Tablette : {}".format(server_url))

    if awareness:
        print("[..] startAwareness...")
        awareness.setEngagementMode("FullyEngaged")
        awareness.startAwareness()
        print("[OK] Awareness")

    print("[..] Salutation...")
    animated.say("Bonjour ! Je suis votre assistant d accueil.")
    print("[OK] Salutation")

    # Démarrer le thread TTS (toujours actif)
    tts_poller = TTSPoller(server_url, animated.say)
    tts_poller.start()
    print("[OK] Thread TTS démarré")

    # Charger ALAudioRecorder (nécessaire pour MicController et STT)
    print("[..] Chargement ALAudioRecorder...")
    recorder = load_service("ALAudioRecorder")

    # Démarrer le MicController (bouton micro tablette, toujours actif)
    mic_ctrl = None
    if recorder:
        mic_ctrl = MicController(server_url, recorder, tts_poller)
        mic_ctrl.start()
        print("[OK] Thread MicController démarré")
    else:
        print("[WARN] ALAudioRecorder indisponible — bouton micro désactivé")

    # Démarrer STT continu si demandé (ancien mode)
    stt_loop = None
    if enable_stt and recorder:
        stt_loop = STTLoop(server_url, asr_url, recorder, tts, tts_poller)
        stt_loop.start()
        print("[OK] Thread STT démarré")

    print("[OK] En attente — Ctrl+C pour arrêter")
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n[..] Arrêt.")
    finally:
        tts_poller.stop()
        if mic_ctrl:
            mic_ctrl.stop()
        if stt_loop:
            stt_loop.stop()
        motion.rest()
        app.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server",      default="http://127.0.0.1:5000")
    parser.add_argument("--asr",         default="http://127.0.0.1:5001")
    parser.add_argument("--pepper-ip",   default="127.0.0.1")
    parser.add_argument("--pepper-port", default=9559, type=int)
    parser.add_argument("--stt",         action="store_true", help="Activer le STT")
    args = parser.parse_args()
    run(args.server, args.asr, args.pepper_ip, args.pepper_port, enable_stt=args.stt)
