from celery import shared_task


@shared_task
def test_celery_task():
    """Celery altyapısının çalıştığını doğrulamak için test görevi."""
    return "Celery çalışıyor."
