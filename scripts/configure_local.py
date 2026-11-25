"""Create private local settings without overwriting existing configuration."""
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / ".env"
if not path.exists():
    values = {
        "JWT_SECRET": secrets.token_urlsafe(48),
        "POSTGRES_PASSWORD": secrets.token_urlsafe(24),
        "RESEARCH_REGISTRATION_CODE": secrets.token_urlsafe(18),
    }
    try:
        with path.open("x", encoding="utf-8") as file:
            file.write("# Private local configuration. Keep this file out of source control.\n")
            file.writelines(f"{key}={value}\n" for key, value in values.items())
    except FileExistsError:
        pass
    print("Private local settings are available in .env.")
else:
    print("Using existing .env settings.")
