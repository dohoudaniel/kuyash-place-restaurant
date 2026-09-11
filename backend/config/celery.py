"""Celery application.

Local development runs with CELERY_TASK_ALWAYS_EAGER, so no broker is required.
"""

from __future__ import annotations

import os
from typing import Any

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("kuyash")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self: Any) -> str:  # pragma: no cover - diagnostic helper
    return f"request: {self.request!r}"
