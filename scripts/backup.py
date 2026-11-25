"""Take an online database backup. Restore to a separate database before testing it."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.db import engine


def backup(destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    if engine.dialect.name == "sqlite":
        target = destination / f"demandtwin-{stamp}.db"
        with sqlite3.connect(engine.url.database) as source, sqlite3.connect(target) as output:
            source.backup(output)
            result = output.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise RuntimeError("SQLite backup integrity check failed")
    elif engine.dialect.name == "postgresql":
        binary = shutil.which("pg_dump")
        if not binary:
            raise RuntimeError("Install PostgreSQL client tools and put pg_dump on PATH")
        target = destination / f"demandtwin-{stamp}.dump"
        url = engine.url
        env = {**os.environ, "PGPASSWORD": url.password or ""}
        subprocess.run([binary, "-h", url.host or "localhost", "-p", str(url.port or 5432),
                        "-U", url.username or "", "-d", url.database, "-Fc", "-f", str(target)],
                       check=True, env=env)
    else:
        raise RuntimeError("Unsupported database dialect")
    print(f"Database backup saved to {target}")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "backups")
    backup(parser.parse_args().directory)
