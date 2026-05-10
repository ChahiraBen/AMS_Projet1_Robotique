# AMS_Projet1_Robotique — Assistant d'accueil hospitalier avec Pepper

Projet tutoré M1 IA — Université d'Avignon  
Réalisé par : Chahira Benzouaoua et Hadjira Taleb

---

## Présentation

Ce projet est un assistant d'accueil hospitalier basé sur le robot **Pepper** de SoftBank Robotics.  
Il permet à un patient d'interagir vocalement ou via une tablette pour :
- Trouver un service ou un médecin dans l'hôpital
- Consulter les horaires et les contacts
- Prendre un rendez-vous médical
- Obtenir un itinéraire guidé pas à pas sur la tablette

L'architecture repose sur un serveur **Flask** (Python) qui expose une API REST, un **LLM** (GPT-4o-mini via OpenAI) pour comprendre les questions en langage naturel, et un script Python qui tourne directement **sur le robot Pepper**.

---

## Architecture générale

```
┌─────────────────────────────────────────────────┐
│                  Robot Pepper                   │
│  pepper/robot_script.py                         │
│  - TTSPoller : fait parler Pepper               │
│  - MicController : enregistre la voix           │
│  - Tablette : affiche l'interface web           │
└────────────────┬────────────────────────────────┘
                 │ HTTP (REST API)
┌────────────────▼────────────────────────────────┐
│             Serveur Flask (Python 3)            │
│                                                 │
│  app.py — point d'entrée                        │
│  config.py — variables d'environnement          │
│                                                 │
│  controllers/                                   │
│    chatbot_controller.py — routes /chatbot      │
│    conversations_controller.py — routes /conv   │
│                                                 │
│  services/                                      │
│    dialog_service.py — GPT + function calling   │
│    hospital_service.py — aiguilleur métier      │
│                                                 │
│  repositories/                                  │
│    conv_repo.py — conversations (SQLite)        │
│    hospital_repo.py — données hôpital (SQLite)  │
│    db.py — connexion base de données            │
│                                                 │
│  static/js/                                     │
│    chat.js — interface de chat (JS)             │
│    hospital_map.js — carte interactive (Canvas) │
│                                                 │
│  templates/                                     │
│    welcome.html — page d'accueil                │
│    index.html — interface de chat               │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│         SQLite — data/hopital_fictif.db         │
│  Tables : Hopital, Service, Medecin,            │
│           Pharmacie, Disponibilites,            │
│           RendezVous, Conversations, Messages   │
└─────────────────────────────────────────────────┘
```

---

## Flux d'une conversation

1. L'utilisateur envoie un message (texte ou vocal)
2. `chatbot_controller.py` reçoit la requête HTTP
3. `dialog_service.py` envoie l'historique + le message à GPT-4o-mini
4. GPT décide d'appeler un **outil** (function calling) si nécessaire
5. `hospital_service.py` reçoit l'intention et les entités extraites par GPT
6. `hospital_repo.py` exécute la requête SQL correspondante
7. Le résultat est renvoyé à GPT qui formule la réponse finale
8. La réponse est sauvegardée en base et renvoyée au client

---

## Description des fichiers

### `app.py`
Point d'entrée du serveur Flask. Crée l'application, enregistre les blueprints (groupes de routes), définit les routes `/` (page d'accueil) et `/chat` (interface de conversation). Lance aussi la récupération des conversations orphelines au démarrage.

---

### `config.py`
Lit les variables d'environnement depuis le fichier `.env` : clé API OpenAI, modèle GPT utilisé, chemin vers la base de données SQLite, clé secrète Flask.

---

### `controllers/chatbot_controller.py`
Groupe de routes HTTP liées au chatbot :
- `POST /chatbot` — reçoit un message, appelle `DialogService`, renvoie la réponse
- `GET /updates` — renvoie les messages envoyés par le robot depuis la dernière vérification
- `POST /speak/push` — reçoit un texte à faire lire par Pepper
- `GET /speak` — le robot vient récupérer le texte à dire
- `POST /mic/start` et `POST /mic/stop` — démarrage/arrêt de l'enregistrement vocal
- `GET /mic/status` — état actuel du micro (pour le robot)
- `POST /transcribe` — reçoit un fichier audio WAV, le transcrit avec Whisper

---

### `controllers/conversations_controller.py`
Groupe de routes HTTP pour gérer les conversations :
- `GET /conversations` — liste toutes les conversations
- `POST /conversations` — crée une nouvelle conversation
- `DELETE /conversations/<id>` — supprime une conversation et ses messages
- `GET /conversations/<id>/messages` — retourne l'historique d'une conversation

---

### `services/dialog_service.py`
Le cœur du système. Gère le dialogue avec GPT-4o-mini via l'API OpenAI.

- Construit le contexte de conversation (les 10 derniers messages)
- Définit le prompt système qui donne à GPT son rôle d'assistant hospitalier
- Déclare les **outils** (function calling) : `query_hospital`, `get_available_slots`, `book_appointment`
- Exécute une boucle : GPT répond → si un outil est appelé → on l'exécute → on renvoie le résultat à GPT → GPT formule la réponse finale
- Détecte si la réponse concerne une localisation pour activer la carte interactive

---

### `services/hospital_service.py`
Couche intermédiaire entre `dialog_service` et `hospital_repo`. Reçoit une intention et des entités (nom de service, nom de médecin) et appelle la méthode correspondante du repository. Permet de séparer la logique métier de l'accès aux données.

---

### `repositories/hospital_repo.py`
Toutes les requêtes SQL liées aux données hospitalières :
- Recherche d'un service (localisation, horaires, contact)
- Recherche d'un médecin (par nom, spécialité, service)
- Calcul des créneaux disponibles pour un médecin (en fonction de ses disponibilités et des rendez-vous déjà pris)
- Réservation d'un rendez-vous
- Parsing de dates en format libre ("5 mai", "15/05", "2026-05-15")

---

### `repositories/conv_repo.py`
Accès SQLite pour les conversations et les messages :
- Créer, lister, supprimer des conversations
- Ajouter un message à une conversation
- Mettre à jour le titre d'une conversation (premier message utilisateur)
- Récupérer les messages d'une conversation (historique)
- Récupérer les conversations orphelines au démarrage (messages sans conversation parente)

---

### `repositories/db.py`
Fonctions utilitaires de connexion à SQLite. Configure `row_factory` pour accéder aux colonnes par leur nom. Expose `query_one()`, `query_all()` et `get_connection()`.

---

### `pepper/robot_script.py`
Script Python 2.7 qui tourne **directement sur le robot Pepper** (pas sur le serveur).

- Se connecte à NAOqi (l'OS de Pepper) via le SDK `qi`
- Charge les services NAOqi : `ALTextToSpeech` (voix), `ALMotion` (corps), `ALBasicAwareness` (regard), `ALTabletService` (écran), `ALAudioRecorder` (micro)
- **TTSPoller** : thread qui interroge `/speak` toutes les secondes et fait parler Pepper avec `tts.say()`
- **MicController** : thread qui gère l'enregistrement audio — démarre/arrête selon l'état de `/mic/status`, envoie l'audio à `/transcribe`, envoie la transcription à `/chatbot`
- `_clean_tts()` : nettoie les caractères typographiques (guillemets courbes, etc.) avant la synthèse vocale pour éviter que NAOqi les interprète comme des commandes d'animation

---

### `static/js/chat.js`
Interface de chat côté navigateur :
- Gestion des conversations (créer, supprimer, changer, afficher l'historique)
- Envoi des messages au serveur et affichage des réponses
- Animation "..." pendant que le serveur traite la requête
- Polling toutes les secondes de `/updates` pour récupérer les messages du robot
- Activation du bouton Plan quand le chatbot détecte une demande de localisation
- Gestion du bouton micro

---

### `static/js/hospital_map.js`
Carte interactive de l'hôpital dessinée sur un `<canvas>` HTML :
- Plan schématique des bâtiments (Urgences, Cardiologie, Radiologie, etc.)
- Animation d'un chemin en pointillés bleus depuis l'entrée jusqu'au service demandé
- Guide pas à pas avec boutons Précédent/Suivant
- Callback TTS : chaque étape du guide est envoyée à `/speak/push` pour être lue par Pepper
- Mode "plan général" : tous les bâtiments cliquables

---

### `templates/welcome.html`
Page d'accueil statique présentant Pepper et les fonctionnalités disponibles. Contient un bouton de redirection vers l'interface de chat.

---

### `templates/index.html`
Interface de chat principale. Définit la structure HTML : sidebar (liste des conversations), zone de messages, panneau carte, panneau informations, formulaire de saisie. Les scripts `hospital_map.js` et `chat.js` sont chargés en bas de page.

---

## Installation et lancement

### Serveur (PC / serveur réseau)

```bash
pip install -r requirements.txt
python app.py
```

Le serveur écoute sur `http://0.0.0.0:5000`.

### Robot Pepper

```bash
python pepper/robot_script.py --server http://<IP_SERVEUR>:5000 --pepper-ip 127.0.0.1
```

Voir [pepper/install.md](chatbot/pepper/install.md) pour les détails d'installation sur Pepper.

---

## Technologies utilisées

| Composant | Technologie |
|---|---|
| Serveur web | Flask (Python 3) |
| LLM | GPT-4o-mini (OpenAI) |
| Base de données | SQLite |
| Transcription vocale | Whisper (OpenAI) |
| Synthèse vocale | NAOqi ALTextToSpeech |
| Robot | Pepper (SoftBank Robotics) |
| Interface web | HTML / CSS / JavaScript vanilla |
| Carte interactive | Canvas HTML5 |
