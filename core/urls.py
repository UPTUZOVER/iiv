from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
# ====================
# Swagger / Redoc konfiguratsiyasi
# ====================
schema_view = get_schema_view(
    openapi.Info(
        title="My Project API",
        default_version='v1',
        description="API documentation for my project",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# ====================
# URL Patterns
# ====================
urlpatterns = [
    # Swagger va Redoc
    path('swagger<format>.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # JWT token refresh
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Admin panel
    path('admin/', admin.site.urls),

    # App URLs
    path('', include('main_video.urls')),  # main_video app ichidagi url-larni chaqiradi
]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)