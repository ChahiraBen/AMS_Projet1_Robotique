import json
from typing import Any, Dict
from services.ollama_client import generate_text
from dialog.context import history_to_text

PROMPT_NLU = """
Tu es un module NLU pour un robot d’accueil d’hôpital.
Ton rôle est de classifier l'intention et d'extraire les entités correspondant aux colonnes de la base de données.

INTENTS : localisation_medecin, localisation_service, horaires_service, contact_service, information_pharmacie, salutation, au_revoir, inconnu.

ENTITÉS (Colonnes BD) :
nom_service (ex: cardiologie, urgences)
nom_medecin (ex: Martin)
specialite (ex: cardiologie)  # utile pour localisation_medecin avec OR
nom_hopital
nom_pharmacie

RÈGLES STRICTES :
- Choisis un seul intent.
- Extrais les entités présentes dans la phrase. Si une entité est absente, mets null.
- Réponds UNIQUEMENT en JSON valide (sans texte autour, sans markdown).

INTERDIT :
- ```json
- ```
- tout texte hors JSON

Historique :
{history}

Phrase utilisateur :
"{user_text}"


""".strip()
def _safe_parse_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()

    # enlever les fences ```json ... ```
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]  # retire la première ligne (``` ou ```json)
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]  # retire la dernière ligne ```
        text = "\n".join(lines).strip()

    # tentative directe
    try:
        return json.loads(text)
    except Exception:
        # fallback: extraire bloc {...}
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end+1])
        raise ValueError("Impossible de parser le JSON renvoyé par Ollama")


def extract_intent_entities(user_text: str, history: list[dict]) -> Dict[str, Any]:
    prompt = PROMPT_NLU.format(history=history_to_text(history), user_text=user_text)
    raw = generate_text(prompt)
    data = _safe_parse_json(raw)

    # Normaliser un peu
    intent = data.get("intent", "inconnu")
    entities = data.get("entities") or {}

    # garantir clés attendues
    entities.setdefault("nom_service", None)
    entities.setdefault("nom_medecin", None)
    entities.setdefault("specialite", None)
    entities.setdefault("nom_hopital", None)
    entities.setdefault("nom_pharmacie", None)

    return {"intent": intent, "entities": entities, "raw": raw}
