from collections import defaultdict, deque
from typing import Any, Dict, List

class ContextStore:
    def __init__(self, max_turns: int = 8):
        self.max_turns = max_turns
        self._store = defaultdict(lambda: deque(maxlen=max_turns))
        self._state = defaultdict(lambda: {"last_service": None, "last_medecin": None, "last_specialite": None})

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        return list(self._store[session_id])

    def append_turn(self, session_id: str, user: str, assistant: str):
        self._store[session_id].append({"user": user, "assistant": assistant})

    def get_state(self, session_id: str) -> Dict[str, Any]:
        return self._state[session_id]

    def set_last(self, session_id: str, nom_service=None, nom_medecin=None, specialite=None):
        st = self._state[session_id]
        if nom_service is not None:
            st["last_service"] = nom_service
        if nom_medecin is not None:
            st["last_medecin"] = nom_medecin
        if specialite is not None:
            st["last_specialite"] = specialite

def history_to_text(history: List[Dict[str, Any]]) -> str:
    if not history:
        return "(vide)"
    lines = []
    for t in history:
        lines.append(f"Utilisateur: {t['user']}")
        lines.append(f"Assistant: {t['assistant']}")
    return "\n".join(lines)
