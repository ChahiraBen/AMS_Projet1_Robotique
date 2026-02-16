from typing import Any, Dict, Tuple
from db.database import fetch_one, fetch_all
from db import queries

def run_intent(intent: str, entities: Dict[str, Any]) -> Tuple[Any, str | None]:
    """
    Retourne (data, need_clarification)
    - data: résultat DB (dict, list, ou None)
    - need_clarification: string si il manque une entité (ex: "nom_service")
    """

    if intent == "salutation":
        return {"type": "static", "text": "Bonjour, comment puis-je vous aider ?"}, None

    if intent == "localisation_service":
        if not entities.get("nom_service"):
            return None, "nom_service"
        row = fetch_one(queries.SQL_LOCALISATION_SERVICE, {"nom_service": entities["nom_service"]})
        return row, None

    if intent == "horaires_service":
        if not entities.get("nom_service"):
            return None, "nom_service"
        row = fetch_one(queries.SQL_HORAIRES_SERVICE, {"nom_service": entities["nom_service"]})
        return row, None

    if intent == "localisation_medecin":
        # vous acceptez nom_medecin OU specialite
        nom_med = entities.get("nom_medecin")
        spec = entities.get("specialite")
        if not nom_med and not spec:
            return None, "nom_medecin_ou_specialite"
        row = fetch_one(queries.SQL_LOCALISATION_MEDECIN, {"nom_medecin": nom_med, "specialite": spec})
        return row, None

    if intent == "contact_service":
        if not entities.get("nom_service"):
            return None, "nom_service"
        row = fetch_one(queries.SQL_CONTACT_SERVICE, {"nom_service": entities["nom_service"]})
        return row, None

    if intent == "information_pharmacie":
        rows = fetch_all(queries.SQL_INFO_PHARMACIE, {})
        return rows, None

    return None, None

def clarification_text(need: str) -> str:
    if need == "nom_service":
        return "Pour quel service exactement ? (ex: cardiologie, radiologie, urgences)"
    if need == "nom_medecin_ou_specialite":
        return "Quel est le nom du médecin ou la spécialité recherchée ? (ex: Docteur Martin ou cardiologie)"
    return "Pouvez-vous préciser votre demande ?"
