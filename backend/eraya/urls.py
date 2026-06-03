from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/agents/', include('apps.agents.urls')),
    path('api/decisions/', include('apps.decisions.urls')),
    path('api/incidents/', include('apps.incidents.urls')),
    path('api/audit/', include('apps.audit.urls')),
    path('api/domains/', include('apps.domains.urls')),
    # KAVACHA security simulation endpoints (additive)
    path('api/v1/security/', include('apps.security.urls')),
]
