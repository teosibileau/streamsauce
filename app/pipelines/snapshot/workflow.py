"""DBOS workflow for the snapshot pipeline."""

from dbos import DBOS

from .events import SnapshotEvent
from .steps import annotate_snapshot, detect_objects, log_snapshot


@DBOS.workflow()
def process_snapshot(
    camera_id: str,
    snapshot_url: str,
    snapshot_epoch: int,
    segment_url: str,
    segment_epoch: int,
):
    log_result = log_snapshot(
        camera_id, snapshot_url, snapshot_epoch, segment_url, segment_epoch
    )
    DBOS.set_event(SnapshotEvent.SNAPSHOT_RECEIVED, log_result)

    detection_result = detect_objects(snapshot_url, camera_id, snapshot_epoch)
    DBOS.set_event(SnapshotEvent.DETECTION_COMPLETE, detection_result)

    if not detection_result:
        return {**log_result, "detections": detection_result}

    annotate_result = annotate_snapshot(
        snapshot_url, camera_id, snapshot_epoch, detection_result
    )
    DBOS.set_event(SnapshotEvent.ANNOTATION_SAVED, annotate_result)

    return {**log_result, "detections": detection_result}
