from google import genai
from config import Config
from utils.prompts import ANSWER_PROMPT

class ResponseService:
    def __init__(self):
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)

    def generate(self, question, history, data):
        prompt = ANSWER_PROMPT.format(question=question, history=history, data=data)
        try:
            resp = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
            )
            text = (resp.text or "").strip()
            return text or "Je ne dispose pas de cette information."
        except Exception:
            return "Je ne dispose pas de cette information."
