"""Modelos de la app accounts: Contrata (tenant), User custom y Trabajador."""
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class Contrata(models.Model):
    """Empresa contratista: unidad de aislamiento multi-tenant.

    Todos los datos operativos del sistema cuelgan (directa o
    indirectamente) de una contrata; los querysets de la API se filtran
    siempre por ``request.user.contrata``.
    """

    nombre = models.CharField("nombre", max_length=150)
    slug = models.SlugField("slug", unique=True)
    cif = models.CharField("CIF", max_length=20, blank=True)
    activa = models.BooleanField("activa", default=True)
    creado = models.DateTimeField("creado", auto_now_add=True)
    modificado = models.DateTimeField("modificado", auto_now=True)

    class Meta:
        verbose_name = "contrata"
        verbose_name_plural = "contratas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class User(AbstractUser):
    """Usuario del sistema con rol y contrata.

    ``contrata`` solo puede ser nula para el superadministrador de la
    plataforma (is_superuser); cualquier otro usuario debe pertenecer a
    una contrata para que el aislamiento multi-tenant funcione.
    """

    class Rol(models.TextChoices):
        ADMIN_CONTRATA = "ADMIN_CONTRATA", "Administrador de contrata"
        CAPATAZ = "CAPATAZ", "Capataz"
        FUSIONADOR = "FUSIONADOR", "Fusionador"

    contrata = models.ForeignKey(
        Contrata,
        verbose_name="contrata",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usuarios",
        help_text="Nulo solo para el superadministrador de la plataforma.",
    )
    rol = models.CharField(
        "rol", max_length=20, choices=Rol.choices, default=Rol.FUSIONADOR
    )

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        if self.contrata_id:
            return f"{self.username} ({self.contrata.slug})"
        return self.username


class Trabajador(models.Model):
    """Operario de la contrata; puede tener o no usuario asociado."""

    # Nota de diseño: se añade FK a contrata (no está explícita en el SPEC)
    # para poder filtrar trabajadores por tenant aunque no tengan usuario.
    contrata = models.ForeignKey(
        Contrata,
        verbose_name="contrata",
        on_delete=models.CASCADE,
        related_name="trabajadores",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trabajador",
    )
    nombre = models.CharField("nombre", max_length=150)
    cuadrilla = models.CharField("cuadrilla", max_length=100, blank=True)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "trabajador"
        verbose_name_plural = "trabajadores"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
