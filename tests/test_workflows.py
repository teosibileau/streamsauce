"""Tests for DBOS workflows and steps."""

from app.workflows import log_segment, log_snapshot, process_segment, process_snapshot


def test_log_snapshot_returns_expected_dict():
    result = log_snapshot(
        "cam1",
        "http://nginx/cam1/snap.jpg",
        1711195203,
        "http://nginx/cam1/seg.ts",
        1711195200,
    )
    assert result == {
        "camera_id": "cam1",
        "snapshot_epoch": 1711195203,
        "status": "received",
        "segment_url": "http://nginx/cam1/seg.ts",
        "segment_epoch": 1711195200,
    }


def test_log_segment_returns_expected_dict():
    result = log_segment(
        "cam1", "http://nginx/cam1/seg.ts", 1711195200, "http://nginx/cam1/stream.m3u8"
    )
    assert result == {
        "camera_id": "cam1",
        "segment_epoch": 1711195200,
        "status": "received",
    }


def test_log_snapshot_preserves_camera_id():
    result = log_snapshot("cam99", "http://x", 1, "http://y", 2)
    assert result["camera_id"] == "cam99"


def test_log_segment_preserves_camera_id():
    result = log_segment("cam99", "http://x", 1, "http://y")
    assert result["camera_id"] == "cam99"


def test_process_snapshot_is_dbos_workflow():
    assert hasattr(process_snapshot, "dbos_function_name")


def test_process_segment_is_dbos_workflow():
    assert hasattr(process_segment, "dbos_function_name")


def test_log_snapshot_is_dbos_step():
    assert hasattr(log_snapshot, "dbos_function_name")


def test_log_segment_is_dbos_step():
    assert hasattr(log_segment, "dbos_function_name")
