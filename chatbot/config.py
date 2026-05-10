import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv(override=True)


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    DB_PATH = os.getenv("DB_PATH", "data/hopital.db")
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
