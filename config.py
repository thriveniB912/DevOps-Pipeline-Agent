import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./opsmemory.db"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
HINDSIGHT_URL = os.getenv("HINDSIGHT_URL", "")
HINDSIGHT_BANK = os.getenv("HINDSIGHT_BANK", "opsmemory")
