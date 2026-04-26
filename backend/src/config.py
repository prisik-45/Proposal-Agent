import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Vercel serverless limits file writing. Fall back to /tmp/ directory for generation.
if "VERCEL" in os.environ or os.environ.get("VERCEL_ENV") or os.environ.get("PORT"):
    OUTPUT_DIR = Path("/tmp/output")
else:
    OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

AGENCY_NAME = os.getenv("AGENCY_NAME", "Tarkshy")
AGENCY_LOGO_PATH = os.getenv("AGENCY_LOGO_PATH", "")
AGENCY_DEMO_LINK = os.getenv("AGENCY_DEMO_LINK", "https://example.com/demo")
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://proposal-agent-eight.vercel.app,http://localhost:5173",
).split(",")
AGENCY_SERVICES = [
    "AI Automation",
    "Web Development",
    "Social Media Management",
]

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_CLIENT_SECRET_FILE = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "client_secret.json")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
GOOGLE_OAUTH_TOKEN_FILE = os.getenv("GOOGLE_OAUTH_TOKEN_FILE", "token.json")
GOOGLE_OAUTH_HOST = os.getenv("GOOGLE_OAUTH_HOST", "localhost")
GOOGLE_OAUTH_PORT = int(os.getenv("GOOGLE_OAUTH_PORT", "8080"))
