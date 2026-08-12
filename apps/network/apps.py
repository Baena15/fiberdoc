"""Configuración de la app network (modelo topológico de red FTTH)."""
from django.apps import AppConfig


class NetworkConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.network"
    verbose_name = "Red"
