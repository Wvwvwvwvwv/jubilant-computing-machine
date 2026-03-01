from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional

from services.task_runner import TaskRunner, TaskRecord

router = APIRouter()


class TaskCreateRequest(BaseModel):
    goal: str = Field(..., min_length=3, max_length=4000)
    max_attempts: int = Field(3, ge=1, le=10)
    approval_required: bool = False


class TaskEventResponse(BaseModel):
    ts: float
    kind: str
    message: str
    payload: dict


class TaskResponse(BaseModel):
    task_id: str
    goal: str
    status: str
    attempt: int
    max_attempts: int
    created_at: float
    updated_at: float
    last_error: Optional[str] = None
    error_class: Optional[str] = None
    approval_required: bool
    approved: bool
    events: List[TaskEventResponse]


class TaskListResponse(BaseModel):
    items: List[TaskResponse]
    count: int


def to_response(rec: TaskRecord) -> TaskResponse:
    return TaskResponse(
        task_id=rec.task_id,
        goal=rec.goal,
        status=rec.status.value,
        attempt=rec.attempt,
        max_attempts=rec.max_attempts,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
        last_error=rec.last_error,
        error_class=rec.error_class,
        approval_required=rec.approval_required,
        approved=rec.approved,
        events=[
            TaskEventResponse(ts=e.ts, kind=e.kind, message=e.message, payload=e.payload)
            for e in rec.events
        ],
    )


@router.post("/", response_model=TaskResponse)
async def create_task(body: TaskCreateRequest, req: Request):
    runner: TaskRunner = req.app.state.task_runner
    rec = runner.create_task(
        goal=body.goal,
        max_attempts=body.max_attempts,
        approval_required=body.approval_required,
    )
    return to_response(rec)


@router.post("/{task_id}/approve", response_model=TaskResponse)
async def approve_task(task_id: str, req: Request):
    runner: TaskRunner = req.app.state.task_runner
    rec = runner.get_task(task_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Task not found")
    return to_response(runner.approve_task(task_id))


@router.post("/{task_id}/run", response_model=TaskResponse)
async def run_task(task_id: str, req: Request):
    runner: TaskRunner = req.app.state.task_runner
    rec = runner.get_task(task_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Task not found")
    return to_response(runner.run_once(task_id))


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, req: Request):
    runner: TaskRunner = req.app.state.task_runner
    rec = runner.get_task(task_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Task not found")
    return to_response(rec)


@router.get("/", response_model=TaskListResponse)
async def list_tasks(req: Request, limit: int = 50):
    runner: TaskRunner = req.app.state.task_runner
    items = [to_response(x) for x in runner.list_tasks(limit=limit)]
    return TaskListResponse(items=items, count=len(items))
