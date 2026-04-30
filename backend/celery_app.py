"""Celery application instance.

Workers start via: celery -A backend.celery_app worker --loglevel=info
"""

from celery import Celery

from backend.config import REDIS_URL

celery = Celery(
    "boke",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # SQLite is single-writer — one worker concurrency avoids contention
    worker_concurrency=1,
    # Results are stored in DB directly; expire Celery results quickly
    result_expires=300,
    task_default_queue="default",
)
