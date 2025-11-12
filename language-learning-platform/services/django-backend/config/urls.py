"""URL Configuration."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # API endpoints
    path('api/v1/languages/', include('apps.languages.urls')),
    path('api/v1/concepts/', include('apps.concepts.urls')),
    path('api/v1/spaced-repetition/', include('apps.spaced_repetition.urls')),
    path('api/v1/ai-content/', include('apps.ai_content.urls')),
    path('api/v1/tutoring/', include('apps.tutoring.urls')),
    path('api/v1/users/', include('apps.users.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
