"""Tests for application lifespan."""

import importlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def test_lifespan_startup_and_shutdown():
    call_order = []

    mock_dbos_cls = MagicMock()
    mock_dbos_cls.launch.side_effect = lambda: call_order.append("dbos_launch")

    mock_consumer = MagicMock()
    mock_consumer.start = AsyncMock(
        side_effect=lambda: call_order.append("consumer_start")
    )
    mock_consumer.stop = AsyncMock(
        side_effect=lambda: call_order.append("consumer_stop")
    )

    # Remove cached module so we can re-import with mocks
    sys.modules.pop("app.main", None)

    with patch("dbos.DBOS", mock_dbos_cls), patch(
        "app.consumer.AMQPConsumer", return_value=mock_consumer
    ):
        import app.main

        importlib.reload(app.main)

        with TestClient(app.main.app):
            assert "dbos_launch" in call_order
            assert "consumer_start" in call_order
            assert call_order.index("dbos_launch") < call_order.index("consumer_start")

        assert "consumer_stop" in call_order

    # Cleanup
    sys.modules.pop("app.main", None)
