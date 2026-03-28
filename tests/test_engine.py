"""Tests for the ONNX detection engine."""

from unittest.mock import MagicMock, patch

import numpy as np
import supervision as sv

from app.detection.engine import TARGET_CLASSES, OnnxDetector


def _make_mock_session(input_shape=(1, 3, 640, 640), input_name="images"):
    session = MagicMock()
    input_meta = MagicMock()
    input_meta.name = input_name
    input_meta.shape = list(input_shape)
    session.get_inputs.return_value = [input_meta]
    return session


def _make_yolo_output(num_detections=3, num_classes=80):
    """Build fake YOLO output: shape (1, 4+num_classes, num_detections).

    Engine's _postprocess expects this shape and does output[0].T
    to get (num_detections, 4+num_classes).
    """
    boxes = np.array(
        [
            [320, 240, 100, 200],
            [100, 100, 50, 50],
            [500, 400, 80, 120],
        ],
        dtype=np.float32,
    )[:num_detections]

    scores = np.zeros((num_detections, num_classes), dtype=np.float32)
    if num_detections >= 1:
        scores[0, 0] = 0.95  # person
    if num_detections >= 2:
        scores[1, 2] = 0.80  # car
    if num_detections >= 3:
        scores[2, 16] = 0.70  # dog

    # Shape: (num_detections, 84) → transpose to (84, num_detections) → add batch
    data = np.concatenate([boxes, scores], axis=1).T
    return np.expand_dims(data, axis=0)  # (1, 84, N)


class TestPreprocess:
    def _make_detector(self):
        with patch("onnxruntime.InferenceSession", return_value=_make_mock_session()):
            return OnnxDetector("fake.onnx", ["CPUExecutionProvider"], 0.25)

    def test_output_shape(self):
        detector = self._make_detector()
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        blob, scale_x, scale_y = detector._preprocess(image)
        assert blob.shape == (1, 3, 640, 640)
        assert blob.dtype == np.float32

    def test_values_normalized(self):
        detector = self._make_detector()
        image = np.full((480, 640, 3), 255, dtype=np.uint8)
        blob, _, _ = detector._preprocess(image)
        assert blob.min() >= 0.0
        assert blob.max() <= 1.0

    def test_scale_factors(self):
        detector = self._make_detector()
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        _, scale_x, scale_y = detector._preprocess(image)
        assert scale_x == 640 / 640
        assert scale_y == 480 / 640


class TestPostprocess:
    def _make_detector(self, confidence_threshold=0.25):
        with patch("onnxruntime.InferenceSession", return_value=_make_mock_session()):
            return OnnxDetector(
                "fake.onnx", ["CPUExecutionProvider"], confidence_threshold
            )

    def test_returns_detections(self):
        detector = self._make_detector()
        output = _make_yolo_output()
        # _postprocess expects shape (1, 84, N) — it does output[0].T
        detections = detector._postprocess(output, 1.0, 1.0)
        assert isinstance(detections, sv.Detections)
        assert len(detections) > 0

    def test_empty_when_below_confidence(self):
        detector = self._make_detector(confidence_threshold=0.99)
        output = _make_yolo_output()
        detections = detector._postprocess(output, 1.0, 1.0)
        assert len(detections) == 0

    def test_filters_by_target_class(self):
        detector = self._make_detector()
        output = _make_yolo_output()

        # Modify to have a non-target class detection
        raw = output.copy()
        # In transposed form: row 4+class_id, col = detection_index
        raw[0, 4 + 50, 1] = 0.99  # Override detection 1 with class 50
        raw[0, 4 + 2, 1] = 0.0  # Remove car score from detection 1

        detections = detector._postprocess(raw, 1.0, 1.0)
        for cid in detections.class_id:
            assert cid in TARGET_CLASSES

    def test_rescales_coordinates(self):
        detector = self._make_detector()
        output = _make_yolo_output(num_detections=1)

        detections_1x = detector._postprocess(output, 1.0, 1.0)
        detections_2x = detector._postprocess(output, 2.0, 2.0)

        if len(detections_1x) > 0 and len(detections_2x) > 0:
            np.testing.assert_allclose(
                detections_2x.xyxy[0], detections_1x.xyxy[0] * 2.0, rtol=1e-5
            )


class TestDetect:
    def test_end_to_end_with_mock_session(self):
        mock_session = _make_mock_session()
        output = _make_yolo_output()
        # session.run returns a list; detect() does outputs[0] then passes to _postprocess
        mock_session.run.return_value = [output]

        with patch("onnxruntime.InferenceSession", return_value=mock_session):
            detector = OnnxDetector("fake.onnx", ["CPUExecutionProvider"], 0.25)

        image = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = detector.detect(image)

        assert isinstance(detections, sv.Detections)
        mock_session.run.assert_called_once()


class TestGetDetector:
    @patch("app.detection.engine._detector", None)
    @patch("app.detection.engine.onnx_config")
    @patch("onnxruntime.InferenceSession", return_value=_make_mock_session())
    def test_lazy_singleton(self, mock_session_cls, mock_config):
        from app.detection.engine import get_detector

        mock_config.model_path = "fake.onnx"
        mock_config.execution_provider = "CPUExecutionProvider"
        mock_config.confidence_threshold = 0.25

        d1 = get_detector()
        d2 = get_detector()
        assert d1 is d2
