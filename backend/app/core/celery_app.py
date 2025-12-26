from celery import Celery
from backend.app.core.config import settings

if settings.REDIS_URL:
    broker_url = settings.REDIS_URL
else:
    broker_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

celery_app = Celery("martin_worker", broker=broker_url)

celery_app.conf.task_routes = {
    "backend.app.services.tasks.send_meeting_reminders": "periodic",
    "backend.app.services.tasks.generate_project_pdf": "formatting",
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
