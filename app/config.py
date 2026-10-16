import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "app.db"

DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_LLM_MODEL = os.getenv("SARVAM_LLM_MODEL", "sarvam-105b-conversations")
