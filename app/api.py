"""API endpoints."""

from typing import Optional

from dbos import DBOS
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/workflows")
async def list_workflows(
    status: Optional[str] = Query(default="PENDING", description="Filter by status"),
    start_time: Optional[str] = Query(default=None, description="RFC 3339 timestamp"),
    end_time: Optional[str] = Query(default=None, description="RFC 3339 timestamp"),
    name: Optional[str] = Query(default=None, description="Workflow function name"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    sort_desc: bool = Query(default=True),
):
    workflows = DBOS.list_workflows(
        status=status,
        start_time=start_time,
        end_time=end_time,
        name=name,
        limit=limit,
        offset=offset,
        sort_desc=sort_desc,
        load_input=False,
        load_output=False,
    )
    return [
        {
            "workflow_id": wf.workflow_id,
            "name": wf.name,
            "status": wf.status,
            "created_at": wf.created_at,
            "updated_at": wf.updated_at,
        }
        for wf in workflows
    ]


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    wf = DBOS.get_workflow_status(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "workflow_id": wf.workflow_id,
        "name": wf.name,
        "status": wf.status,
        "input": wf.input,
        "output": wf.output,
        "error": wf.error,
        "created_at": wf.created_at,
        "updated_at": wf.updated_at,
        "queue_name": wf.queue_name,
        "executor_id": wf.executor_id,
    }
