import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from app.db.session import create_db_engine

API_ROOT = Path(__file__).resolve().parents[1]


async def test_alembic_upgrade_and_database_round_trip() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=API_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr

    engine = create_db_engine(os.environ["DATABASE_URL"])
    try:
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT 1")) == 1
            version = await connection.scalar(text("SELECT version_num FROM alembic_version"))
    finally:
        await engine.dispose()

    assert version == "0001_baseline"
