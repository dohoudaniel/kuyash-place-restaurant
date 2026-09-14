"""Root URL configuration."""

from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.accounts.urls import account_urlpatterns, auth_urlpatterns
from apps.catalog.urls import wishlist_urlpatterns
from apps.common.views import (
    api_bad_request,
    api_not_found,
    api_permission_denied,
    api_server_error,
    health_check,
)
from apps.payments.urls import webhook_urlpatterns

admin.site.site_header = settings.ADMIN_SITE_HEADER
admin.site.site_title = settings.ADMIN_SITE_TITLE
admin.site.index_title = settings.ADMIN_INDEX_TITLE

api_v1 = [
    path("core/", include("apps.core.urls")),
    path("auth/", include((auth_urlpatterns, "auth"))),
    path("catalog/", include("apps.catalog.urls")),
    path("cart/", include("apps.carts.urls")),
    path("orders/", include("apps.orders.urls")),
    path("kds/", include("apps.orders.kds_urls")),
    path("payments/", include("apps.payments.urls")),
    path("reservations/", include("apps.reservations.urls")),
    path("catering/", include("apps.catering.urls")),
    path("support/", include("apps.support.urls")),
    path("reviews/", include("apps.reviews.urls")),
    path("gallery/", include("apps.gallery.urls")),
    path("academy/", include("apps.academy.urls")),
    path("loyalty/", include("apps.loyalty.urls")),
    path("reports/", include("apps.reporting.urls")),
    path("wishlist/", include((wishlist_urlpatterns, "wishlist"))),
    path("webhooks/", include((webhook_urlpatterns, "webhooks"))),
    path("accounts/", include((account_urlpatterns, "accounts"))),
]

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("health/", health_check, name="health-check"),
    path("api/v1/", include((api_v1, "v1"))),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/v1/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # allauth headless: JSON auth endpoints for the decoupled frontend.
    path("_allauth/", include("allauth.headless.urls")),
    # Provider callbacks (e.g. /accounts/google/login/callback/). Under
    # HEADLESS_ONLY this include exposes nothing but those routes — and without
    # it every social sign-in fails with NoReverseMatch before reaching Google.
    # Register these URLs in the Google and Facebook developer consoles.
    path("accounts/", include("allauth.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Every response this service produces is JSON, including the failures.
handler400 = api_bad_request
handler403 = api_permission_denied
handler404 = api_not_found
handler500 = api_server_error
