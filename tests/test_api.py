"""Tests for API endpoints."""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("app.api.DBOS")
def test_list_workflows_default(mock_dbos):
    wf = MagicMock()
    wf.workflow_id = "cam1-snapshot-100"
    wf.name = "process_snapshot"
    wf.status = "PENDING"
    wf.created_at = 1711195200000
    wf.updated_at = 1711195200000
    mock_dbos.list_workflows.return_value = [wf]

    response = client.get("/workflows")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["workflow_id"] == "cam1-snapshot-100"
    assert data[0]["status"] == "PENDING"
    mock_dbos.list_workflows.assert_called_once_with(
        status="PENDING",
        start_time=None,
        end_time=None,
        name=None,
        limit=50,
        offset=0,
        sort_desc=True,
        load_input=False,
        load_output=False,
    )


@patch("app.api.DBOS")
def test_list_workflows_with_filters(mock_dbos):
    mock_dbos.list_workflows.return_value = []

    response = client.get(
        "/workflows?status=SUCCESS&limit=10&offset=5&sort_desc=false&name=process_segment"
    )

    assert response.status_code == 200
    assert response.json() == []
    mock_dbos.list_workflows.assert_called_once_with(
        status="SUCCESS",
        start_time=None,
        end_time=None,
        name="process_segment",
        limit=10,
        offset=5,
        sort_desc=False,
        load_input=False,
        load_output=False,
    )


@patch("app.api.DBOS")
def test_get_workflow_found(mock_dbos):
    wf = MagicMock()
    wf.workflow_id = "cam1-snapshot-100"
    wf.name = "process_snapshot"
    wf.status = "SUCCESS"
    wf.input = {"args": ["cam1", "http://x", 100, "http://y", 90]}
    wf.output = {"camera_id": "cam1", "status": "received"}
    wf.error = None
    wf.created_at = 1711195200000
    wf.updated_at = 1711195201000
    wf.queue_name = None
    wf.executor_id = "proc-1"
    mock_dbos.get_workflow_status.return_value = wf

    response = client.get("/workflows/cam1-snapshot-100")

    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == "cam1-snapshot-100"
    assert data["status"] == "SUCCESS"
    assert data["output"] == {"camera_id": "cam1", "status": "received"}
    assert data["error"] is None


@patch("app.api.DBOS")
def test_get_workflow_not_found(mock_dbos):
    mock_dbos.get_workflow_status.return_value = None

    response = client.get("/workflows/nonexistent")

    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow not found"
