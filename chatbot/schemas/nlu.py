from typing import Any, Dict, Literal, Optional

Intent = Literal[
    "salutation",
    "au_revoir",
    "localisation_service",
    "horaires_service",
    "localisation_medecin",
    "contact_service",
    "information_pharmacie",
    "inconnu",
]


def default_entities() -> Dict[str, Optional[str]]:
    return {
        "nom_service": None,
        "nom_medecin": None,
        "nom_hopital": None,
        "nom_pharmacie": None,
    }


def default_nlu_result() -> Dict[str, Any]:
    return {"intent": "inconnu", "entities": default_entities()}


def normalize_nlu_result(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return default_nlu_result()

    intent = payload.get("intent")
    entities = payload.get("entities")

    allowed_intents = {
        "salutation",
        "au_revoir",
        "localisation_service",
        "horaires_service",
        "localisation_medecin",
        "contact_service",
        "information_pharmacie",
        "inconnu",
    }
    if intent not in allowed_intents:
        intent = "inconnu"

    normalized = default_entities()
    if isinstance(entities, dict):
        for key in normalized:
            val = entities.get(key)
            normalized[key] = val.strip() if isinstance(val, str) and val.strip() else None

    return {"intent": intent, "entities": normalized}
