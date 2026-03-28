"""Tests for snapshot detection and annotation steps."""

from unittest.mock import MagicMock, patch

import numpy as np
import supervision as sv

from app.pipelines.snapshot.steps import (
    COCO_CLASS_NAMES,
    _annotate_image,
    _reconstruct_detections,
    _serialize_detections,
)


def _make_detections(n=3):
    return sv.Detections(
        xyxy=np.array(
            [[10, 20, 100, 200], [50, 60, 150, 250], [200, 200, 300, 350]],
            dtype=np.float32,
        )[:n],
        confidence=np.array([0.95, 0.80, 0.70], dtype=np.float32)[:n],
        class_id=np.array([0, 2, 16], dtype=np.int32)[:n],
    )


def test_serialize_detections_structure():
    detections = _make_detections()
    result = _serialize_detections(detections)
    assert result["count"] == 3
    assert len(result["xyxy"]) == 3
    assert len(result["confidence"]) == 3
    assert len(result["class_id"]) == 3
    assert len(result["class_names"]) == 3


def test_serialize_detections_class_names():
    detections = _make_detections()
    result = _serialize_detections(detections)
    assert result["class_names"] == ["person", "car", "dog"]


def test_serialize_detections_empty():
    detections = sv.Detections.empty()
    result = _serialize_detections(detections)
    assert result["count"] == 0
    assert result["xyxy"] == []
    assert result["confidence"] == []
    assert result["class_id"] == []
    assert result["class_names"] == []


def test_reconstruct_detections_roundtrip():
    original = _make_detections()
    serialized = _serialize_detections(original)
    reconstructed = _reconstruct_detections(serialized)
    assert len(reconstructed) == len(original)
    np.testing.assert_array_almost_equal(reconstructed.xyxy, original.xyxy)
    np.testing.assert_array_almost_equal(reconstructed.confidence, original.confidence)
    np.testing.assert_array_equal(reconstructed.class_id, original.class_id)


def test_reconstruct_detections_empty():
    serialized = _serialize_detections(sv.Detections.empty())
    reconstructed = _reconstruct_detections(serialized)
    assert len(reconstructed) == 0


def test_annotate_image_returns_ndarray():
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = _make_detections()
    annotated = _annotate_image(image, detections)
    assert isinstance(annotated, np.ndarray)
    assert annotated.shape == image.shape


def test_annotate_image_does_not_mutate_original():
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    original = image.copy()
    detections = _make_detections()
    _annotate_image(image, detections)
    np.testing.assert_array_equal(image, original)


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


@patch("app.pipelines.snapshot.steps.requests")
def test_download_image_uses_requests(mock_requests):
    from app.pipelines.snapshot.steps import _download_image

    fake_content = np.zeros((10, 10, 3), dtype=np.uint8)
    _, encoded = __import__("cv2").imencode(".jpg", fake_content)
    mock_response = MagicMock()
    mock_response.content = encoded.tobytes()
    mock_response.raise_for_status = MagicMock()
    mock_requests.get.return_value = mock_response

    image = _download_image("http://fake/image.jpg")
    mock_requests.get.assert_called_once_with("http://fake/image.jpg")
    assert isinstance(image, np.ndarray)
