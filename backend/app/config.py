import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
UPLOADS = DATA / "uploads"
OUTPUTS = DATA / "outputs"
CHROMA = DATA / "chroma"
for p in (UPLOADS, OUTPUTS, CHROMA):
    p.mkdir(parents=True, exist_ok=True)

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
STUDENT_EMAILS = [e.strip() for e in os.getenv("STUDENT_EMAILS", "").split(",") if e.strip()]
EMAIL_WHITELIST = [e.strip().lower() for e in os.getenv("EMAIL_WHITELIST", "").split(",") if e.strip()]
