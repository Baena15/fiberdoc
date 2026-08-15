"""Rutas de autenticación SPA (sesión Django) para el frontend React."""
from django.urls import path

from .api_views import api_login, api_logout, api_me

urlpatterns = [
    path("login/", api_login, name="api-auth-login"),
    path("logout/", api_logout, name="api-auth-logout"),
    path("me/", api_me, name="api-auth-me"),
]
