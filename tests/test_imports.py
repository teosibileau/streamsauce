"""Verify all app modules import without errors."""


def test_import_config():
    import app.config  # noqa: F401


def test_import_api():
    import app.api  # noqa: F401


def test_import_schemas():
    import app.schemas  # noqa: F401


def test_import_consumer():
    import app.consumer  # noqa: F401


def test_import_main():
    import app.main  # noqa: F401


def test_import_snapshot_steps():
    import app.pipelines.snapshot.steps  # noqa: F401


def test_import_snapshot_workflow():
    import app.pipelines.snapshot.workflow  # noqa: F401


def test_import_segment_steps():
    import app.pipelines.segment.steps  # noqa: F401


def test_import_segment_workflow():
    import app.pipelines.segment.workflow  # noqa: F401


def test_import_detection_engine():
    import app.detection.engine  # noqa: F401
