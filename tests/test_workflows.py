"""Tests for DBOS workflows and steps."""

from unittest.mock import patch

from app.pipelines.segment.steps import log_segment
from app.pipelines.segment.workflow import process_segment
from app.pipelines.snapshot.steps import log_snapshot
from app.pipelines.snapshot.workflow import process_snapshot


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


@patch("app.pipelines.snapshot.workflow.DBOS")
@patch("app.pipelines.snapshot.workflow.annotate_snapshot")
@patch("app.pipelines.snapshot.workflow.detect_objects")
@patch("app.pipelines.snapshot.workflow.log_snapshot")
def test_process_snapshot_returns_log_and_detections(
    mock_log, mock_detect, mock_annotate, mock_dbos
):
    mock_log.return_value = {"camera_id": "cam1", "status": "received"}
    mock_detect.return_value = {"count": 2, "class_names": ["person", "car"]}
    mock_annotate.return_value = {"annotated_image": "output/annotations/cam1/123.jpg"}

    result = process_snapshot.__wrapped__(
        "cam1", "http://x/snap.jpg", 123, "http://x/seg.ts", 100
    )

    assert result is not None
    assert result["camera_id"] == "cam1"
    assert result["status"] == "received"
    assert result["detections"]["count"] == 2
    assert result["detections"]["class_names"] == ["person", "car"]


def test_snapshot_event_enum_values():
    from app.pipelines.snapshot.events import SnapshotEvent

    assert SnapshotEvent.SNAPSHOT_RECEIVED == "snapshot_received"
    assert SnapshotEvent.DETECTION_COMPLETE == "detection_complete"
    assert SnapshotEvent.ANNOTATION_SAVED == "annotation_saved"
