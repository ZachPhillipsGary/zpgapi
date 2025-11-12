"""URL Configuration."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from .routers import router

# Customize admin site
admin.site.site_header = "MALA Language Learning Admin"
admin.site.site_title = "MALA Admin"
admin.site.index_title = "Language Learning Platform Administration"

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API endpoints (auto-registered via router)
    path('api/v1/', include(router.urls)),

    # Auth endpoints
    path('api/v1/auth/', include('apps.users.urls')),

    # AI Prompts Management
    path('api/v1/ai-prompts/', include('apps.ai_prompts.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
