"""ONNX-based object detection engine using YOLO + supervision."""

import logging

import cv2
import numpy as np
import onnxruntime as ort
import supervision as sv

from app.config import onnx_config

logger = logging.getLogger(__name__)

PERSON = 0
CAR = 2
MOTORCYCLE = 3
BUS = 5
TRUCK = 7
ANIMAL_IDS = set(range(14, 24))
TARGET_CLASSES = np.array(sorted({PERSON, CAR, MOTORCYCLE, BUS, TRUCK} | ANIMAL_IDS))


class OnnxDetector:
    def __init__(
        self, model_path: str, providers: list[str], confidence_threshold: float
    ):
        self.confidence_threshold = confidence_threshold
        self.session = ort.InferenceSession(model_path, providers=providers)
        input_meta = self.session.get_inputs()[0]
        self.input_name = input_meta.name
        self.input_height = input_meta.shape[2]
        self.input_width = input_meta.shape[3]
        logger.info(
            "OnnxDetector loaded: model=%s provider=%s input=%dx%d",
            model_path,
            providers[0],
            self.input_width,
            self.input_height,
        )

    def _preprocess(self, image: np.ndarray) -> tuple[np.ndarray, float, float]:
        h, w = image.shape[:2]
        scale_x = w / self.input_width
        scale_y = h / self.input_height
        resized = cv2.resize(image, (self.input_width, self.input_height))
        blob = resized.astype(np.float32) / 255.0
        blob = blob.transpose(2, 0, 1)
        blob = np.expand_dims(blob, axis=0)
        return blob, scale_x, scale_y

    def _postprocess(
        self, output: np.ndarray, scale_x: float, scale_y: float
    ) -> sv.Detections:
        predictions = output[0].T

        scores = predictions[:, 4:]
        class_ids = np.argmax(scores, axis=1)
        confidences = scores[np.arange(len(scores)), class_ids]

        mask = confidences > self.confidence_threshold
        predictions = predictions[mask]
        confidences = confidences[mask]
        class_ids = class_ids[mask]

        if len(predictions) == 0:
            return sv.Detections.empty()

        cx, cy, w, h = (
            predictions[:, 0],
            predictions[:, 1],
            predictions[:, 2],
            predictions[:, 3],
        )
        x1 = (cx - w / 2) * scale_x
        y1 = (cy - h / 2) * scale_y
        x2 = (cx + w / 2) * scale_x
        y2 = (cy + h / 2) * scale_y
        xyxy = np.stack([x1, y1, x2, y2], axis=1)

        detections = sv.Detections(
            xyxy=xyxy.astype(np.float32),
            confidence=confidences.astype(np.float32),
            class_id=class_ids.astype(np.int32),
        )

        detections = detections[np.isin(detections.class_id, TARGET_CLASSES)]
        detections = detections.with_nms(threshold=0.5)

        return detections

    def detect(self, image: np.ndarray) -> sv.Detections:
        blob, scale_x, scale_y = self._preprocess(image)
        outputs = self.session.run(None, {self.input_name: blob})
        return self._postprocess(outputs[0], scale_x, scale_y)


_detector: OnnxDetector | None = None


def get_detector() -> OnnxDetector:
    global _detector
    if _detector is None:
        _detector = OnnxDetector(
            model_path=onnx_config.model_path,
            providers=[onnx_config.execution_provider],
            confidence_threshold=onnx_config.confidence_threshold,
        )
    return _detector
