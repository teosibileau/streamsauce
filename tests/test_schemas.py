"""Tests for schemas and routing key parsing."""

from app.schemas import SegmentEvent, SnapshotEvent, parse_routing_key


def test_parse_routing_key_snapshot():
    camera_id, event_type = parse_routing_key("streamchop.cam1.snapshot")
    assert camera_id == "cam1"
    assert event_type == "snapshot"


def test_parse_routing_key_segment():
    camera_id, event_type = parse_routing_key("streamchop.cam1.segment")
    assert camera_id == "cam1"
    assert event_type == "segment"


def test_snapshot_idempotency_key():
    event = SnapshotEvent(
        camera_id="cam1",
        snapshot="snap_1711195203.jpg",
        snapshot_url="http://nginx:80/cam1/snap_1711195203.jpg",
        snapshot_epoch=1711195203,
        segment="segment_1711195200.ts",
        segment_url="http://nginx:80/cam1/segment_1711195200.ts",
        segment_epoch=1711195200,
        timestamp="2026-03-23T12:00:03+00:00",
    )
    assert event.idempotency_key == "cam1-snapshot-1711195203"


def test_segment_idempotency_key():
    event = SegmentEvent(
        camera_id="cam1",
        segment="segment_1711195200.ts",
        playlist="http://nginx:80/cam1/stream.m3u8",
        segment_url="http://nginx:80/cam1/segment_1711195200.ts",
        segment_epoch=1711195200,
        timestamp="2026-03-23T12:00:00+00:00",
    )
    assert event.idempotency_key == "cam1-segment-1711195200"


def test_idempotency_key_deterministic():
    kwargs = dict(
        camera_id="cam1",
        snapshot="snap_1.jpg",
        snapshot_url="http://a",
        snapshot_epoch=100,
        segment="seg_1.ts",
        segment_url="http://b",
        segment_epoch=90,
        timestamp="2026-01-01T00:00:00+00:00",
    )
    assert (
        SnapshotEvent(**kwargs).idempotency_key
        == SnapshotEvent(**kwargs).idempotency_key
    )
