from django.apps import AppConfig


class LoyaltyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.loyalty"
    verbose_name = "Loyalty"

    def ready(self) -> None:
        from apps.loyalty import receivers  # noqa: F401
