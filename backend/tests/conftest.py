import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config


@pytest.fixture(scope="session", autouse=True)
def database(tmp_path_factory):
    path = tmp_path_factory.mktemp("demandtwin") / "test.db"
    os.environ["DATABASE_URL"] = os.getenv("DEMANDTWIN_TEST_POSTGRES") or f"sqlite:///{path.as_posix()}"
    os.environ["RESEARCH_REGISTRATION_CODE"] = "isolated-test-code"
    os.environ["JWT_SECRET"] = "isolated-test-secret-with-more-than-32-characters"
    os.environ["SECURE_COOKIES"] = "0"
    os.environ["CELERY_BROKER_URL"] = ""
    os.environ["ETHICS_PROTOCOL_ID"] = ""
    command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")
