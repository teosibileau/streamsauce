"""Verify all app modules import without errors."""


def test_import_config():
    import app.config  # noqa: F401


def test_import_api():
    import app.api  # noqa: F401


def test_import_workflows():
    import app.workflows  # noqa: F401


def test_import_main():
    import app.main  # noqa: F401
