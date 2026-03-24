"""Message schemas for streamchop events."""

from pydantic import BaseModel


class SnapshotEvent(BaseModel):
    camera_id: str
    snapshot: str
    snapshot_url: str
    snapshot_epoch: int
    segment: str
    segment_url: str
    segment_epoch: int
    timestamp: str

    @property
    def idempotency_key(self) -> str:
        return f"{self.camera_id}-snapshot-{self.snapshot_epoch}"


class SegmentEvent(BaseModel):
    camera_id: str
    segment: str
    playlist: str
    segment_url: str
    segment_epoch: int
    timestamp: str

    @property
    def idempotency_key(self) -> str:
        return f"{self.camera_id}-segment-{self.segment_epoch}"


def parse_routing_key(routing_key: str) -> tuple[str, str]:
    """Parse 'prefix.camera_id.event_type' -> (camera_id, event_type)."""
    parts = routing_key.split(".")
    return parts[-2], parts[-1]
