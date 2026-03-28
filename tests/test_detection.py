"""Tests for snapshot detection and annotation steps."""

from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import supervision as sv

from app.pipelines.snapshot.steps import COCO_CLASS_NAMES


def _make_fake_jpeg(width=640, height=480):
    image = np.zeros((height, width, 3), dtype=np.uint8)
    _, encoded = cv2.imencode(".jpg", image)
    return encoded.tobytes()


def _mock_requests_get(content):
    mock_response = MagicMock()
    mock_response.content = content
    mock_response.raise_for_status = MagicMock()
    return mock_response


def test_coco_class_names_contains_target_classes():
    assert COCO_CLASS_NAMES[0] == "person"
    assert COCO_CLASS_NAMES[2] == "car"
    assert COCO_CLASS_NAMES[16] == "dog"
    assert COCO_CLASS_NAMES[7] == "truck"


def test_detect_objects_step_is_dbos_step():
    from app.pipelines.snapshot.steps import detect_objects

    assert hasattr(detect_objects, "dbos_function_name")


def test_annotate_snapshot_step_is_dbos_step():
    from app.pipelines.snapshot.steps import annotate_snapshot

    assert hasattr(annotate_snapshot, "dbos_function_name")


@patch("app.pipelines.snapshot.steps.get_detector")
@patch("app.pipelines.snapshot.steps.requests")
def test_detect_objects_returns_expected_structure(mock_requests, mock_get_detector):
    from app.pipelines.snapshot.steps import detect_objects

    mock_requests.get.return_value = _mock_requests_get(_make_fake_jpeg())

    mock_detector = MagicMock()
    mock_detector.detect.return_value = sv.Detections(
        xyxy=np.array([[10, 20, 100, 200]], dtype=np.float32),
        confidence=np.array([0.95], dtype=np.float32),
        class_id=np.array([0], dtype=np.int32),
    )
    mock_get_detector.return_value = mock_detector

    result = detect_objects("http://fake/snap.jpg", "cam1", 123456)

    assert result["count"] == 1
    assert result["class_names"] == ["person"]
    assert result["camera_id"] == "cam1"
    assert result["snapshot_epoch"] == 123456
    assert len(result["xyxy"]) == 1
    assert len(result["confidence"]) == 1
    assert len(result["class_id"]) == 1
    assert "detection_epoch" in result
    assert "detection_latency" in result
    assert isinstance(result["detection_epoch"], int)
    assert isinstance(result["detection_latency"], int)


@patch("app.pipelines.snapshot.steps.time")
@patch("app.pipelines.snapshot.steps.get_detector")
@patch("app.pipelines.snapshot.steps.requests")
def test_detect_objects_latency(mock_requests, mock_get_detector, mock_time):
    from app.pipelines.snapshot.steps import detect_objects

    mock_requests.get.return_value = _mock_requests_get(_make_fake_jpeg())

    mock_detector = MagicMock()
    mock_detector.detect.return_value = sv.Detections(
        xyxy=np.array([[10, 20, 100, 200]], dtype=np.float32),
        confidence=np.array([0.95], dtype=np.float32),
        class_id=np.array([0], dtype=np.int32),
    )
    mock_get_detector.return_value = mock_detector
    mock_time.time.return_value = 123459.0

    result = detect_objects("http://fake/snap.jpg", "cam1", 123456)

    assert result["detection_epoch"] == 123459
    assert result["detection_latency"] == 3


@patch("app.pipelines.snapshot.steps.get_detector")
@patch("app.pipelines.snapshot.steps.requests")
def test_detect_objects_empty_detections(mock_requests, mock_get_detector):
    from app.pipelines.snapshot.steps import detect_objects

    mock_requests.get.return_value = _mock_requests_get(_make_fake_jpeg())

    mock_detector = MagicMock()
    mock_detector.detect.return_value = sv.Detections.empty()
    mock_get_detector.return_value = mock_detector

    result = detect_objects("http://fake/snap.jpg", "cam1", 123456)

    assert result is None


def test_persist_detection_step_is_dbos_step():
    from app.pipelines.snapshot.steps import persist_detection

    assert hasattr(persist_detection, "dbos_function_name")


def test_persist_detection_writes_json(tmp_path):
    from app.pipelines.snapshot.steps import persist_detection

    detection_result = {
        "count": 1,
        "xyxy": [[10, 20, 100, 200]],
        "confidence": [0.95],
        "class_id": [0],
        "class_names": ["person"],
        "camera_id": "cam1",
        "snapshot_epoch": 123456,
        "detection_epoch": 123459,
        "detection_latency": 3,
    }

    with patch("app.pipelines.snapshot.steps.Path") as mock_path_cls:
        mock_path = MagicMock()
        mock_path_cls.return_value.__truediv__ = lambda s, x: mock_path
        mock_path.__truediv__ = lambda s, x: mock_path
        mock_path.mkdir = MagicMock()
        mock_path.write_text = MagicMock()

        result = persist_detection("cam1", 123456, detection_result)

    assert "detection_json" in result
    mock_path.write_text.assert_called_once()
    import json

    written = mock_path.write_text.call_args[0][0]
    assert json.loads(written) == detection_result


@patch("app.pipelines.snapshot.steps.cv2.imwrite")
@patch("app.pipelines.snapshot.steps.requests")
def test_annotate_snapshot_saves_image(mock_requests, mock_imwrite, tmp_path):
    from app.pipelines.snapshot.steps import annotate_snapshot

    mock_requests.get.return_value = _mock_requests_get(_make_fake_jpeg())

    detection_result = {
        "count": 1,
        "xyxy": [[10, 20, 100, 200]],
        "confidence": [0.95],
        "class_id": [0],
        "class_names": ["person"],
    }

    with patch("app.pipelines.snapshot.steps.Path") as mock_path_cls:
        MagicMock()
        mock_path_cls.return_value.__truediv__ = lambda s, x: mock_path_cls.return_value
        mock_path_cls.return_value.mkdir = MagicMock()

        result = annotate_snapshot(
            "http://fake/snap.jpg", "cam1", 123456, detection_result
        )

    assert "annotated_image" in result
    mock_imwrite.assert_called_once()
