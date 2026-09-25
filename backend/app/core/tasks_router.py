from fastapi import APIRouter
from celery.result import AsyncResult
from app.core.celery_app import celery_app

router = APIRouter(prefix="/api/v1", tags=["tasks"])


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> dict:
    result = AsyncResult(task_id, app=celery_app)
    if result.state == "PENDING":
        return {"status": "pending", "result": None}
    if result.state == "SUCCESS":
        return {"status": "success", "result": result.result}
    if result.state == "FAILURE":
        return {"status": "failure", "result": {"error": str(result.result)}}
    return {"status": "pending", "result": None}
