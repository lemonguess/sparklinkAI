"""Celery应用配置"""
from celery import Celery
from core.config import settings

# 创建Celery应用
celery_app = Celery(
    "sparklinkai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.services.tasks.document_tasks",
        "app.services.tasks.embedding_tasks",
        "app.services.tasks.search_tasks"
    ]
)

# Celery配置
celery_app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_soft_time_limit=300,  # 5分钟软限制
    task_time_limit=600,       # 10分钟硬限制
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_routes={
        "app.services.tasks.document_tasks.*": {"queue": "document_processing"},
        "app.services.tasks.embedding_tasks.*": {"queue": "embedding"},
        "app.services.tasks.search_tasks.*": {"queue": "search"},
    },
    task_default_queue="default",
    task_create_missing_queues=True,
)

# 任务结果过期时间
celery_app.conf.result_expires = 3600  # 1小时

if __name__ == "__main__":
    celery_app.start()