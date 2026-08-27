import os
from celery import Celery, Task
import sentry_sdk

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("erp")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

class SentryContextTask(Task):
    def apply_async(self, *args, **kwargs):
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("task_name", self.name)
            scope.set_context("celery_task", {
                "name": self.name,
                "args": str(args),
                "kwargs": str(kwargs),
            })
            return super().apply_async(*args, **kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("task_name", self.name)
            scope.set_context("celery_task", {
                "name": self.name,
                "task_id": task_id,
                "args": str(args),
                "kwargs": str(kwargs),
            })
            sentry_sdk.capture_exception(exc)
        super().on_failure(exc, task_id, args, kwargs, einfo)