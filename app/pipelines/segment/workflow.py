"""DBOS workflow for the segment pipeline."""

from dbos import DBOS

from .steps import log_segment


@DBOS.workflow()
def process_segment(
    camera_id: str,
    segment_url: str,
    segment_epoch: int,
    playlist: str,
):
    result = log_segment(camera_id, segment_url, segment_epoch, playlist)
    return result
