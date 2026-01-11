"""
URL configuration for Kenya-First LMS.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.admin),
    
    # API endpoints (to be created in respective apps)
    # path('api/', include('api.urls')),
    
    # Webhook endpoints (for payment providers)
    # path('webhooks/', include('webhooks.urls')),
    
    # Main app views (to be created)
    # path('', include('frontend.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

