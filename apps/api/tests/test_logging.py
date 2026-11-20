import json
import logging

from app.core.logging import JsonFormatter


def test_formatter_emits_one_json_object() -> None:
    record = logging.LogRecord(
        name="devsphere.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "devsphere.test"
    assert payload["message"] == "hello"
    assert "timestamp" in payload
