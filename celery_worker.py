"""Celery Worker 启动脚本"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.celery_app import celery_app

if __name__ == "__main__":
    # 启动Celery Worker
    celery_app.start([
        "worker",
        "--loglevel=info",
        "--concurrency=4",
        "--queues=default,document_processing,embedding,search"
    ])