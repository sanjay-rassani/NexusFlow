"""
NexusFlow root URL configuration.
All app URLs are versioned under /api/v1/.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

api_v1_patterns = [
    # Auth endpoints (Phase 2)
    path("auth/", include("apps.users.urls")),
    # Domain endpoints (Phase 3+)
    path("vendors/", include("apps.vendors.urls")),
    path("orders/", include("apps.orders.urls")),
    path("delivery/", include("apps.delivery.urls")),
    path("chat/", include("apps.chat.urls")),
    path("notifications/", include("apps.notifications.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1_patterns)),
]

# Serve media in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Debug toolbar
    try:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
