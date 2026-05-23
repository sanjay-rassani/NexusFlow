"""
Celery application configuration for NexusFlow.
Tasks are autodiscovered from all installed apps.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("nexusflow")

# Pull config from Django settings, namespace CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks — pass the packages explicitly so the worker finds all
# tasks at startup without relying on lazy Django-settings resolution.
app.autodiscover_tasks(
    [
        "apps.users",
        "apps.notifications",
        "apps.orders",
    ]
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
