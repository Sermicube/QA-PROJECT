from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "copiloto",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Bogota",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
celery_app.autodiscover_tasks([
    "app.context",
    "app.testcases",
    "app.testdata",
    "app.evidence",
    "app.deliverables",
])
