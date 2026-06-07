from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Django REST API (unchanged)
    path('api/agents/', include('apps.agents.urls')),
    path('api/decisions/', include('apps.decisions.urls')),
    path('api/incidents/', include('apps.incidents.urls')),
    path('api/audit/', include('apps.audit.urls')),
    path('api/domains/', include('apps.domains.urls')),
    # KAVACHA security simulation endpoints (additive)
    path('api/v1/security/', include('apps.security.urls')),
    # Credential auth
    path('api/eraya-auth/', include('apps.eraya_auth.urls')),
    # Vanilla HTML frontend (catch-all — must be last)
    path('', include('apps.frontend.urls')),
]
