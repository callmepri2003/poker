
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from poker import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'game', views.GameViewSet, basename='game')

# URL patterns
urlpatterns = [
    path('api/v1/', include(router.urls)),
]
