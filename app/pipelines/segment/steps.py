"""DBOS steps for the segment pipeline."""

import logging

from dbos import DBOS

logger = logging.getLogger(__name__)


@DBOS.step()
def log_segment(
    camera_id: str,
    segment_url: str,
    segment_epoch: int,
    playlist: str,
) -> dict:
    logger.info(
        "Processing segment: camera=%s epoch=%d url=%s",
        camera_id,
        segment_epoch,
        segment_url,
    )
    return {
        "camera_id": camera_id,
        "segment_epoch": segment_epoch,
        "status": "received",
    }
