from django.apps import AppConfig


class RealtimeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.realtime"
    verbose_name = "Realtime"

    def ready(self) -> None:
        from apps.realtime import receivers  # noqa: F401
