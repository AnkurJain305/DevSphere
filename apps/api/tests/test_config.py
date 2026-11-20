from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import get_settings
from app.main import create_app


def test_app_refuses_to_boot_when_database_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ValidationError) as caught:
        create_app()

    assert "database_url" in str(caught.value)
    get_settings.cache_clear()
