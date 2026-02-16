import json
from services.ollama_client import generate_text
from dialog.context import history_to_text

PROMPT_NLG = """
Tu es un assistant d’accueil pour un hôpital.
Tu dois répondre uniquement avec les informations fournies dans "data".
Si l’information demandée n’est pas disponible, dis exactement :
"Je ne dispose pas de cette information."

Historique :
{history}

Données extraites de la base :
{data}

Question de l’utilisateur :
{question}
""".strip()

def generate_answer(question: str, history: list[dict], data) -> str:
    prompt = PROMPT_NLG.format(
        history=history_to_text(history),
        data=json.dumps(data, ensure_ascii=False),
        question=question
    )
    out = generate_text(prompt).strip()
    return out or "Je ne dispose pas de cette information."
