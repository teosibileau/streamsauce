"""DBOS steps for the snapshot pipeline."""

import logging
from pathlib import Path

import cv2
import numpy as np
import requests
import supervision as sv
from dbos import DBOS

from app.detection.engine import get_detector

logger = logging.getLogger(__name__)

COCO_CLASS_NAMES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    14: "bird",
    15: "cat",
    16: "dog",
    17: "horse",
    18: "sheep",
    19: "cow",
    20: "elephant",
    21: "bear",
    22: "zebra",
    23: "giraffe",
}

box_annotator = sv.BoxAnnotator()
label_annotator = sv.LabelAnnotator()


@DBOS.step()
def log_snapshot(
    camera_id: str,
    snapshot_url: str,
    snapshot_epoch: int,
    segment_url: str,
    segment_epoch: int,
) -> dict:
    logger.info(
        "Processing snapshot: camera=%s epoch=%d url=%s segment_url=%s segment_epoch=%d",
        camera_id,
        snapshot_epoch,
        snapshot_url,
        segment_url,
        segment_epoch,
    )
    return {
        "camera_id": camera_id,
        "snapshot_epoch": snapshot_epoch,
        "status": "received",
        "segment_url": segment_url,
        "segment_epoch": segment_epoch,
    }


@DBOS.step()
def detect_objects(
    snapshot_url: str,
    camera_id: str,
    snapshot_epoch: int,
) -> dict:
    response = requests.get(snapshot_url)
    response.raise_for_status()
    data = np.frombuffer(response.content, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)

    detector = get_detector()
    detections = detector.detect(image)

    result = {
        "count": len(detections),
        "xyxy": detections.xyxy.tolist(),
        "confidence": (
            detections.confidence.tolist() if detections.confidence is not None else []
        ),
        "class_id": (
            detections.class_id.tolist() if detections.class_id is not None else []
        ),
        "class_names": [
            COCO_CLASS_NAMES.get(cid, str(cid))
            for cid in (detections.class_id if detections.class_id is not None else [])
        ],
        "camera_id": camera_id,
        "snapshot_epoch": snapshot_epoch,
    }
    logger.info(
        "Detection complete: camera=%s epoch=%d objects=%d",
        camera_id,
        snapshot_epoch,
        result["count"],
    )
    return result


@DBOS.step()
def annotate_snapshot(
    snapshot_url: str,
    camera_id: str,
    snapshot_epoch: int,
    detection_result: dict,
) -> dict:
    response = requests.get(snapshot_url)
    response.raise_for_status()
    data = np.frombuffer(response.content, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)

    if detection_result["count"] == 0:
        detections = sv.Detections.empty()
    else:
        detections = sv.Detections(
            xyxy=np.array(detection_result["xyxy"], dtype=np.float32),
            confidence=np.array(detection_result["confidence"], dtype=np.float32),
            class_id=np.array(detection_result["class_id"], dtype=np.int32),
        )

    labels = [
        f"{COCO_CLASS_NAMES.get(cid, str(cid))} {conf:.2f}"  # noqa: E231
        for cid, conf in zip(detections.class_id, detections.confidence)
    ]
    annotated = box_annotator.annotate(scene=image.copy(), detections=detections)
    annotated = label_annotator.annotate(
        scene=annotated, detections=detections, labels=labels
    )

    output_dir = Path("output/annotations") / camera_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{snapshot_epoch}.jpg"
    cv2.imwrite(str(output_path), annotated)

    logger.info(
        "Annotation saved: camera=%s epoch=%d path=%s",
        camera_id,
        snapshot_epoch,
        output_path,
    )
    return {"annotated_image": str(output_path)}
