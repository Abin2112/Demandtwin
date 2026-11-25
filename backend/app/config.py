from pathlib import Path
import os
import secrets

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
RUNTIME = ROOT / "data" / "runtime"
RUNTIME.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{(RUNTIME / 'app.db').as_posix()}"
BROKER = os.getenv("CELERY_BROKER_URL")
SECURE_COOKIES = os.getenv("SECURE_COOKIES") == "1"
RESEARCH_CODE = os.getenv("RESEARCH_REGISTRATION_CODE")
ETHICS_PROTOCOL = os.getenv("ETHICS_PROTOCOL_ID")
ETHICS_CONSENT = os.getenv("ETHICS_CONSENT_TEXT")


def jwt_secret() -> str:
    configured = os.getenv("JWT_SECRET")
    if configured:
        if len(configured) < 32:
            raise RuntimeError("JWT_SECRET must have at least 32 characters")
        return configured
    path = RUNTIME / "local-secret"
    try:
        with path.open("x", encoding="ascii") as file:
            file.write(secrets.token_urlsafe(48))
    except FileExistsError:
        pass
    return path.read_text(encoding="ascii")
