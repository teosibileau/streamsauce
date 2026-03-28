"""Tests for AMQPConsumer message handling."""

import json
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest

from app.config import AMQPConfig
from app.consumer import AMQPConsumer
from app.pipelines.segment.workflow import process_segment
from app.pipelines.snapshot.workflow import process_snapshot

SNAPSHOT_BODY = {
    "camera_id": "cam1",
    "snapshot": "snap_1711195203.jpg",
    "snapshot_url": "http://nginx:80/cam1/snap_1711195203.jpg",
    "snapshot_epoch": 1711195203,
    "segment": "segment_1711195200.ts",
    "segment_url": "http://nginx:80/cam1/segment_1711195200.ts",
    "segment_epoch": 1711195200,
    "timestamp": "2026-03-23T12:00:03+00:00",
}

SEGMENT_BODY = {
    "camera_id": "cam1",
    "segment": "segment_1711195200.ts",
    "playlist": "http://nginx:80/cam1/stream.m3u8",
    "segment_url": "http://nginx:80/cam1/segment_1711195200.ts",
    "segment_epoch": 1711195200,
    "timestamp": "2026-03-23T12:00:00+00:00",
}

CONFIG = AMQPConfig(
    host="localhost",
    port=5672,
    username="guest",
    password="guest",
    exchange="amq.topic",
    queue_name="test.queue",
    routing_keys=["streamchop.*.snapshot", "streamchop.*.segment"],
)


def _make_message(routing_key: str, body: dict) -> MagicMock:
    msg = MagicMock()
    msg.routing_key = routing_key
    msg.body = json.dumps(body).encode()

    @asynccontextmanager
    async def process(requeue=False):
        yield

    msg.process = process
    return msg


@pytest.mark.asyncio
@patch("app.consumer.DBOS")
@patch("app.consumer.SetWorkflowID")
async def test_on_message_snapshot(mock_set_wf_id, mock_dbos):
    consumer = AMQPConsumer(CONFIG)
    msg = _make_message("streamchop.cam1.snapshot", SNAPSHOT_BODY)

    await consumer._on_message(msg)

    mock_dbos.start_workflow.assert_called_once_with(
        process_snapshot,
        "cam1",
        "http://nginx:80/cam1/snap_1711195203.jpg",
        1711195203,
        "http://nginx:80/cam1/segment_1711195200.ts",
        1711195200,
    )


@pytest.mark.asyncio
@patch("app.consumer.DBOS")
@patch("app.consumer.SetWorkflowID")
async def test_on_message_segment(mock_set_wf_id, mock_dbos):
    consumer = AMQPConsumer(CONFIG)
    msg = _make_message("streamchop.cam1.segment", SEGMENT_BODY)

    await consumer._on_message(msg)

    mock_dbos.start_workflow.assert_called_once_with(
        process_segment,
        "cam1",
        "http://nginx:80/cam1/segment_1711195200.ts",
        1711195200,
        "http://nginx:80/cam1/stream.m3u8",
    )


@pytest.mark.asyncio
@patch("app.consumer.DBOS")
@patch("app.consumer.SetWorkflowID")
async def test_on_message_unknown_event_type(mock_set_wf_id, mock_dbos):
    consumer = AMQPConsumer(CONFIG)
    msg = _make_message("streamchop.cam1.unknown", {"camera_id": "cam1"})

    await consumer._on_message(msg)

    mock_dbos.start_workflow.assert_not_called()


@pytest.mark.asyncio
@patch("app.consumer.DBOS")
@patch("app.consumer.SetWorkflowID")
async def test_on_message_sets_workflow_id(mock_set_wf_id, mock_dbos):
    consumer = AMQPConsumer(CONFIG)
    msg = _make_message("streamchop.cam1.snapshot", SNAPSHOT_BODY)

    await consumer._on_message(msg)

    mock_set_wf_id.assert_called_once_with("cam1-snapshot-1711195203")


def test_init_stores_config():
    consumer = AMQPConsumer(CONFIG)
    assert consumer.config is CONFIG
    assert consumer._connection is None
    assert consumer._channel is None
