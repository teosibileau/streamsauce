"""Event constants for the snapshot pipeline."""

from enum import StrEnum


class SnapshotEvent(StrEnum):
    SNAPSHOT_RECEIVED = "snapshot_received"
    DETECTION_COMPLETE = "detection_complete"
    ANNOTATION_SAVED = "annotation_saved"
