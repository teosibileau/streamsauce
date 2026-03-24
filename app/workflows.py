"""DBOS workflows."""

import logging

from dbos import DBOS

logger = logging.getLogger(__name__)


@DBOS.workflow()
def process_snapshot(
    camera_id: str,
    snapshot_url: str,
    snapshot_epoch: int,
    segment_url: str,
    segment_epoch: int,
):
    result = log_snapshot(
        camera_id, snapshot_url, snapshot_epoch, segment_url, segment_epoch
    )
    return result


@DBOS.workflow()
def process_segment(
    camera_id: str,
    segment_url: str,
    segment_epoch: int,
    playlist: str,
):
    result = log_segment(camera_id, segment_url, segment_epoch, playlist)
    return result


@DBOS.step()
def log_snapshot(
    camera_id: str,
    snapshot_url: str,
    snapshot_epoch: int,
    segment_url: str,
    segment_epoch: int,
) -> dict:
    logger.info(
        "Processing snapshot: camera=%s epoch=%d url=%s",
        camera_id,
        snapshot_epoch,
        snapshot_url,
    )
    return {
        "camera_id": camera_id,
        "snapshot_epoch": snapshot_epoch,
        "status": "received",
    }


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
