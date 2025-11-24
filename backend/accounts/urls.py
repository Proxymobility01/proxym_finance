from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from accounts.views import UserViewSet, MeView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('me/', MeView.as_view(), name='me'),
    path('', include(router.urls)),

]
