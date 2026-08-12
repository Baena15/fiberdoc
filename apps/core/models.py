"""Modelos de la app core: Cliente, PerfilOperadora, EsquemaColor y tarifas.

Nota sobre jsonb: se usa ``models.JSONField``, que en PostgreSQL se mapea a
``jsonb`` y en SQLite funciona igualmente para tests (fallback documentado).
"""
from django.core.exceptions import ValidationError
from django.db import models

# Umbrales por defecto: pérdida de fusión (dB) por tipo de fibra.
# ok < SM.ok -> OK; SM.ok <= x < SM.warn -> WARNING; >= warn -> FUERA.
UMBRALES_DEFECTO = {
    "SM": {"ok": 0.05, "warn": 0.10},
    "MM": {"ok": 0.10, "warn": 0.20},
}


class EsquemaColor(models.Model):
    """Esquema de colores de fibra (array ordenado de 12 colores).

    ``contrata`` nula significa esquema global del sistema (DIN/TIA);
    con contrata, es un esquema privado de esa empresa.
    """

    class Ambito(models.TextChoices):
        DIN_VDE0888 = "DIN_VDE0888", "DIN VDE 0888"
        TIA_568 = "TIA_568", "TIA-568"
        PRIVADO = "PRIVADO", "Privado"

    contrata = models.ForeignKey(
        "accounts.Contrata",
        verbose_name="contrata",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="esquemas_color",
        help_text="Nulo = esquema global del sistema.",
    )
    nombre = models.CharField("nombre", max_length=100)
    ambito = models.CharField("ámbito", max_length=20, choices=Ambito.choices)
    colores = models.JSONField(
        "colores",
        help_text="Array ordenado de 12 colores (tubos/fibras 1-12).",
    )

    class Meta:
        verbose_name = "esquema de color"
        verbose_name_plural = "esquemas de color"
        ordering = ["nombre"]

    def clean(self):
        super().clean()
        if not isinstance(self.colores, list) or len(self.colores) != 12:
            raise ValidationError(
                {"colores": "El esquema debe ser un array ordenado de 12 colores."}
            )

    def __str__(self):
        return self.nombre


class Cliente(models.Model):
    """Operadora cliente de la contrata (propietaria de la red)."""

    contrata = models.ForeignKey(
        "accounts.Contrata",
        verbose_name="contrata",
        on_delete=models.CASCADE,
        related_name="clientes",
    )
    nombre = models.CharField("nombre", max_length=150)
    contacto = models.CharField("contacto", max_length=150, blank=True)

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["contrata", "nombre"], name="uniq_cliente_nombre_contrata"
            )
        ]

    def __str__(self):
        return self.nombre


class PerfilOperadora(models.Model):
    """Parámetros técnicos por defecto que la operadora exige en sus obras.

    Las obras copian estos umbrales/potencias al crearse si no se indica
    un perfil explícito (ver ``Obra.save``).
    """

    class Arquitectura(models.TextChoices):
        GPON_CENTRALIZADA = "GPON_CENTRALIZADA", "GPON centralizada"
        GPON_CASCADA = "GPON_CASCADA", "GPON en cascada"
        GPON_DISTRIBUIDA = "GPON_DISTRIBUIDA", "GPON distribuida"
        P2P_SIN_SPLITTER = "P2P_SIN_SPLITTER", "P2P sin splitter"
        MIXTA = "MIXTA", "Mixta"

    cliente = models.ForeignKey(
        Cliente,
        verbose_name="cliente",
        on_delete=models.CASCADE,
        related_name="perfiles",
    )
    nombre = models.CharField("nombre", max_length=100)
    umbrales = models.JSONField(
        "umbrales (dB)",
        default=dict,
        help_text='Formato: {"SM": {"ok": x, "warn": y}, "MM": {...}}',
    )
    potencia_min_dbm = models.DecimalField(
        "potencia mínima (dBm)", max_digits=6, decimal_places=2, null=True, blank=True
    )
    potencia_max_dbm = models.DecimalField(
        "potencia máxima (dBm)", max_digits=6, decimal_places=2, null=True, blank=True
    )
    esquema_color = models.ForeignKey(
        EsquemaColor,
        verbose_name="esquema de color",
        on_delete=models.PROTECT,
        related_name="perfiles",
    )
    arquitectura = models.CharField(
        "arquitectura por defecto",
        max_length=20,
        choices=Arquitectura.choices,
        default=Arquitectura.GPON_CASCADA,
    )
    notas = models.TextField("notas", blank=True)

    class Meta:
        verbose_name = "perfil de operadora"
        verbose_name_plural = "perfiles de operadora"

    def clean(self):
        super().clean()
        if not self.umbrales:
            self.umbrales = UMBRALES_DEFECTO

    def __str__(self):
        return f"{self.cliente} · {self.nombre}"


class TarifaUO(models.Model):
    """Tarifa de unidades de obra acordada con una operadora (cabecera)."""

    cliente = models.ForeignKey(
        Cliente,
        verbose_name="cliente",
        on_delete=models.CASCADE,
        related_name="tarifas",
    )
    codigo = models.CharField("código", max_length=50)
    descripcion = models.CharField("descripción", max_length=200, blank=True)
    vigente = models.BooleanField("vigente", default=True)

    class Meta:
        verbose_name = "tarifa de unidades de obra"
        verbose_name_plural = "tarifas de unidades de obra"
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "codigo"], name="uniq_tarifa_codigo_cliente"
            )
        ]

    def __str__(self):
        return f"{self.codigo} ({self.cliente})"


class TarifaItem(models.Model):
    """Línea de tarifa: código de unidad de obra, precio y unidad."""

    tarifa = models.ForeignKey(
        TarifaUO,
        verbose_name="tarifa",
        on_delete=models.CASCADE,
        related_name="items",
    )
    codigo = models.CharField(
        "código", max_length=50, help_text="Ej.: FUS-EMPALME, MONT-CTO-16, M-TENDIDO."
    )
    descripcion = models.CharField("descripción", max_length=200)
    precio = models.DecimalField("precio (€)", max_digits=10, decimal_places=2)
    unidad = models.CharField("unidad", max_length=20, help_text="Ej.: ud, m, fusión.")

    class Meta:
        verbose_name = "ítem de tarifa"
        verbose_name_plural = "ítems de tarifa"
        constraints = [
            models.UniqueConstraint(
                fields=["tarifa", "codigo"], name="uniq_item_codigo_tarifa"
            )
        ]

    def __str__(self):
        return f"{self.codigo} · {self.precio} €/{self.unidad}"
