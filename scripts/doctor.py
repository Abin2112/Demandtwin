"""Check the local dependencies and database before starting DemandTwin."""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "ml-engine")]
from sqlalchemy import inspect, text
from app.db import engine


def run():
    missing = [name for name in ("node", "npm") if shutil.which(name) is None]
    if missing:
        raise RuntimeError("Install Node.js and npm before starting. Missing " + ", ".join(missing))
    for package in ("fastapi", "uvicorn", "sqlalchemy", "alembic", "numpy", "scipy", "PIL", "reportlab", "sklearn", "celery"):
        __import__(package)
    if not (ROOT / "frontend/node_modules/next/package.json").exists():
        raise RuntimeError("Frontend dependencies are missing. Run scripts/setup.ps1 first.")
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    tables = inspect(engine).get_table_names()
    if "notifications" not in tables or "project_members" not in tables:
        raise RuntimeError("The database needs migrations. Run scripts/setup.ps1.")
    print(f"Ready | Python {sys.version.split()[0]} | database {engine.dialect.name} | migration {revision}")


if __name__ == "__main__":
    try:
        run()
    except Exception as error:
        print(f"Startup check failed: {error}", file=sys.stderr)
        raise SystemExit(1)
