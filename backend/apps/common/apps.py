from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
    verbose_name = "Common"

    def ready(self) -> None:
        from apps.common import checks, client_ip  # noqa: F401  (client_ip registers kuyash.W021)
