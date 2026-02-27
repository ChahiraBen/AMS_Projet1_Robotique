import json
from google import genai
from config import Config
from utils.prompts import NLU_PROMPT
from schemas.nlu import normalize_nlu_result

class NLUService:
    def __init__(self):
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)

    def extract(self, text, history):
        prompt = NLU_PROMPT.format(text=text, history=history)

        try:
            resp = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
            )
            raw = (resp.text or "").strip()
        except Exception:
            return normalize_nlu_result(None)

        # Sécuriser : retirer ```json ``` si présent
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(raw)
        except Exception:
            return normalize_nlu_result(None)

        return normalize_nlu_result(data)
