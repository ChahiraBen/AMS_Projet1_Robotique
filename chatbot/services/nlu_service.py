import json
import re
from google import genai
from config import Config
from utils.prompts import NLU_PROMPT
from schemas.nlu import normalize_nlu_result


# ---------------------------------------------------------------------------
# Fallback NLU : règles par mots-clés quand Gemini est indisponible
# ---------------------------------------------------------------------------

_SERVICES = [
    "cardiologie", "urgences", "radiologie", "pédiatrie", "pediatrie",
    "maternité", "maternite", "neurologie", "chirurgie", "oncologie",
    "psychiatrie", "admissions", "accueil",
]

_PATTERNS = [
    # salutation
    (r"\b(bonjour|salut|hello|bonsoir)\b", "salutation", {}),
    # au_revoir
    (r"\b(au revoir|goodbye|bye|merci|bonne journée)\b", "au_revoir", {}),
    # pharmacie
    (r"\b(pharmacie)\b", "information_pharmacie", {}),
    # contact
    (r"\b(téléphone|tel|contact|numéro|appeler)\b", "contact_service", {}),
    # horaires
    (r"\b(horaire|heure|ouvert|ferme|ouverture|fermeture)\b", "horaires_service", {}),
    # médecin
    (r"\b(docteur|dr\.?|médecin|medecin|chirurgien|spécialiste)\b", "localisation_medecin", {}),
    # localisation service (doit être en dernier pour ne pas écraser médecin)
    (r"\b(service|département|departement|où|ou|trouver|situe|situé|localisation|étage|batiment|bâtiment|salle|aller)\b",
     "localisation_service", {}),
]


def _extract_service(text: str):
    text_lower = text.lower()
    for svc in _SERVICES:
        if svc in text_lower:
            return svc.capitalize()
    return None


def _extract_doctor(text: str):
    # "docteur X", "Dr. X", "Dr X"
    m = re.search(r"\b(?:docteur|dr\.?)\s+([a-zA-ZÀ-ÿ\-]+)", text, re.IGNORECASE)
    if m:
        return "Dr. " + m.group(1).capitalize()
    return None


def _fallback_nlu(text: str):
    text_lower = text.lower()
    intent = "inconnu"
    entities = {"nom_service": None, "nom_medecin": None, "nom_hopital": None, "nom_pharmacie": None}

    for pattern, candidate_intent, _ in _PATTERNS:
        if re.search(pattern, text_lower):
            intent = candidate_intent
            break

    entities["nom_service"] = _extract_service(text)
    entities["nom_medecin"] = _extract_doctor(text)

    # Si on a un médecin détecté, forcer l'intent
    if entities["nom_medecin"]:
        intent = "localisation_medecin"
    # Si on a un service et intent générique, forcer localisation_service
    if entities["nom_service"] and intent in ("inconnu",):
        intent = "localisation_service"

    return {"intent": intent, "entities": entities}


# ---------------------------------------------------------------------------
# Service NLU principal
# ---------------------------------------------------------------------------

class NLUService:
    def __init__(self):
        self._gemini_available = bool(Config.GEMINI_API_KEY)
        if self._gemini_available:
            try:
                self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
            except Exception:
                self._gemini_available = False

    def extract(self, text: str, history) -> dict:
        if self._gemini_available:
            result = self._extract_gemini(text, history)
            if result["intent"] != "inconnu":
                return result
            # Si Gemini retourne "inconnu", essayer le fallback
            fallback = _fallback_nlu(text)
            if fallback["intent"] != "inconnu":
                return normalize_nlu_result(fallback)
            return result

        return normalize_nlu_result(_fallback_nlu(text))

    def _extract_gemini(self, text: str, history) -> dict:
        prompt = NLU_PROMPT.format(text=text, history=history)
        try:
            resp = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
            )
            raw = (resp.text or "").strip()
        except Exception:
            self._gemini_available = False
            return normalize_nlu_result(None)

        raw = raw.replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(raw)
        except Exception:
            return normalize_nlu_result(None)

        return normalize_nlu_result(data)
