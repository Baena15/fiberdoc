"""Configuración de la app core (clientes, perfiles, tarifas)."""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Núcleo (clientes y tarifas)"
