# Installation du module qi pour Pepper

## 1. Installer qi (Python 3)

```bash
pip install qi
pip install paramiko   # pour récupérer l'audio depuis Pepper via SSH
pip install requests
```

> Si `pip install qi` échoue sur Windows, utilise cette alternative :
> ```bash
> pip install qipy
> ```
> Ou télécharge le SDK NAOqi Python depuis :
> https://www.aldebaran.com/en/support/pepper-naoqi-2-9/downloads-softwares

## 2. Trouver l'IP de Pepper

Sur le robot : **appuie sur le bouton poitrine** → Pepper annonce son IP.

Exemple : `192.168.1.42`

## 3. Mettre à jour pepper_client.py

Dans `pepper_client.py`, remplace :
```python
DEFAULT_PEPPER_IP  = "192.168.1.X"    # ← IP de Pepper
DEFAULT_SERVER_URL = "http://127.0.0.1:5000"  # ← IP de TON PC sur le WiFi
```

Pour connaître l'IP de ton PC :
```bash
ipconfig   # Windows
```
→ prends l'adresse IPv4 du réseau WiFi (ex: 192.168.1.10)

## 4. Lancer

Terminal 1 – démarrer le backend :
```bash
cd chatbot/
..\.venv\Scripts\python app.py
```

Terminal 2 – lancer le client Pepper :
```bash
cd chatbot/pepper/
..\.venv\Scripts\python pepper_client.py --pepper-ip 192.168.1.42 --server-url http://192.168.1.10:5000
```

## 5. Architecture

```
[Utilisateur parle]
       ↓
[Microphone Pepper]
       ↓ ALAudioRecorder (WAV)
       ↓ SSH → récupère le fichier
[Backend Flask /transcribe]
       ↓ Google Speech-to-Text
[Backend Flask /chatbot]
       ↓ NLU (Gemini/fallback) + SQLite
[Réponse texte]
       ↓ HTTP → pepper_client.py
[ALAnimatedSpeech] → Pepper parle
[ALTabletService]  → affiche l'interface web
```
