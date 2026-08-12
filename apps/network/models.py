"""Modelos de la app network: topología de la red FTTH.

Invariantes de negocio implementadas (testeadas en pytest):
- I1: un puerto no admite dos fusiones/conexiones activas (índices únicos
  parciales ``WHERE activa`` sobre puerto_a y puerto_b).
- I2: ``puerto_a != puerto_b`` y ambos pertenecen al mismo elemento (clean()).
- I3: pérdida de fusión >= 0 y < 3 dB (CheckConstraint + clean()).
- I4: tubo/fibra de un puerto FIBRA_CABLE dentro del rango del cable (clean()).
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.core.models import UMBRALES_DEFECTO


def umbrales_defecto():
    """Devuelve una copia de los umbrales por defecto (para JSONField)."""
    return {k: dict(v) for k, v in UMBRALES_DEFECTO.items()}


class Obra(models.Model):
    """Proyecto de despliegue de una operadora ejecutado por la contrata."""

    class Arquitectura(models.TextChoices):
        GPON_CENTRALIZADA = "GPON_CENTRALIZADA", "GPON centralizada"
        GPON_CASCADA = "GPON_CASCADA", "GPON en cascada"
        GPON_DISTRIBUIDA = "GPON_DISTRIBUIDA", "GPON distribuida"
        P2P_SIN_SPLITTER = "P2P_SIN_SPLITTER", "P2P sin splitter"
        MIXTA = "MIXTA", "Mixta"

    class Estado(models.TextChoices):
        PLANIFICADA = "PLANIFICADA", "Planificada"
        EN_CURSO = "EN_CURSO", "En curso"
        EJECUTADA = "EJECUTADA", "Ejecutada"
        MEDIDA = "MEDIDA", "Medida"
        VALIDADA = "VALIDADA", "Validada"
        CERTIFICADA = "CERTIFICADA", "Certificada"
        FACTURADA = "FACTURADA", "Facturada"

    contrata = models.ForeignKey(
        "accounts.Contrata",
        verbose_name="contrata",
        on_delete=models.CASCADE,
        related_name="obras",
    )
    cliente = models.ForeignKey(
        "core.Cliente",
        verbose_name="cliente",
        on_delete=models.PROTECT,
        related_name="obras",
    )
    perfil_operadora = models.ForeignKey(
        "core.PerfilOperadora",
        verbose_name="perfil de operadora",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="obras",
        help_text="Si se deja vacío se copian los defaults del perfil del cliente.",
    )
    codigo = models.CharField("código", max_length=50)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    ubicacion = models.CharField(
        "ubicación", max_length=150, blank=True, help_text="Municipio / zona."
    )
    arquitectura = models.CharField(
        "arquitectura", max_length=20, choices=Arquitectura.choices
    )
    estado = models.CharField(
        "estado", max_length=20, choices=Estado.choices, default=Estado.PLANIFICADA
    )
    umbrales = models.JSONField(
        "umbrales (dB)",
        default=dict,
        help_text='Formato: {"SM": {"ok": x, "warn": y}, "MM": {...}}. '
        "Vacío = se copian los del perfil de la operadora al guardar.",
    )
    potencia_min_dbm = models.DecimalField(
        "potencia mínima (dBm)", max_digits=6, decimal_places=2, null=True, blank=True
    )
    potencia_max_dbm = models.DecimalField(
        "potencia máxima (dBm)", max_digits=6, decimal_places=2, null=True, blank=True
    )
    requiere_otdr = models.BooleanField("requiere OTDR", default=False)
    creado = models.DateTimeField("creado", auto_now_add=True)
    modificado = models.DateTimeField("modificado", auto_now=True)

    class Meta:
        verbose_name = "obra"
        verbose_name_plural = "obras"
        ordering = ["-creado"]
        constraints = [
            models.UniqueConstraint(
                fields=["contrata", "codigo"], name="uniq_obra_codigo_contrata"
            )
        ]

    def save(self, *args, **kwargs):
        # Resolver el perfil: si no se indica uno explícito se usa el primero
        # del cliente; en ambos casos se copian sus defaults en los campos
        # vacíos (umbrales, potencias).
        perfil = None
        if self.perfil_operadora_id is not None:
            perfil = self.perfil_operadora
        elif self.cliente_id:
            perfil = self.cliente.perfiles.first()
            if perfil is not None:
                self.perfil_operadora = perfil
        if perfil is not None:
            if not self.umbrales:
                self.umbrales = perfil.umbrales
            if self.potencia_min_dbm is None:
                self.potencia_min_dbm = perfil.potencia_min_dbm
            if self.potencia_max_dbm is None:
                self.potencia_max_dbm = perfil.potencia_max_dbm
        if not self.umbrales:
            # Sin perfil disponible: umbrales genéricos del sistema.
            self.umbrales = umbrales_defecto()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} · {self.cliente.nombre}"


class OrdenTrabajo(models.Model):
    """Orden de trabajo asignada a un trabajador dentro de una obra."""

    class Tipo(models.TextChoices):
        TENDIDO = "TENDIDO", "Tendido"
        FUSION = "FUSION", "Fusión"
        MONTAJE_CTO = "MONTAJE_CTO", "Montaje de CTO"
        MEDICION = "MEDICION", "Medición"
        AVERIA = "AVERIA", "Avería"

    class Estado(models.TextChoices):
        ASIGNADA = "ASIGNADA", "Asignada"
        EN_CURSO = "EN_CURSO", "En curso"
        COMPLETADA = "COMPLETADA", "Completada"
        VALIDADA = "VALIDADA", "Validada"

    obra = models.ForeignKey(
        Obra, verbose_name="obra", on_delete=models.CASCADE, related_name="ordenes"
    )
    tipo = models.CharField("tipo", max_length=20, choices=Tipo.choices)
    trabajador = models.ForeignKey(
        "accounts.Trabajador",
        verbose_name="trabajador",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes",
    )
    fecha = models.DateField("fecha")
    estado = models.CharField(
        "estado", max_length=20, choices=Estado.choices, default=Estado.ASIGNADA
    )

    class Meta:
        verbose_name = "orden de trabajo"
        verbose_name_plural = "órdenes de trabajo"
        ordering = ["-fecha"]

    def __str__(self):
        return f"OT {self.get_tipo_display()} · {self.obra.codigo} · {self.fecha}"


class ElementoRed(models.Model):
    """Elemento físico de la red: empalme, CTO, registro, ODF o caja terminal."""

    class Tipo(models.TextChoices):
        EMPALME = "EMPALME", "Empalme"
        CTO = "CTO", "CTO (caja terminal óptica)"
        REGISTRO = "REGISTRO", "Registro"
        ODF = "ODF", "ODF"
        CJA_TERMINAL = "CJA_TERMINAL", "Caja terminal"

    class UbicacionTipo(models.TextChoices):
        ARQUETA = "ARQUETA", "Arqueta"
        AEREO_FACHADA = "AEREO_FACHADA", "Aéreo en fachada"
        AEREO_POSTE = "AEREO_POSTE", "Aéreo en poste"
        INTERIOR_ICT = "INTERIOR_ICT", "Interior (ICT)"
        CENTRO_ODF = "CENTRO_ODF", "Centro / ODF"

    obra = models.ForeignKey(
        Obra, verbose_name="obra", on_delete=models.CASCADE, related_name="elementos"
    )
    tipo = models.CharField("tipo", max_length=20, choices=Tipo.choices)
    codigo = models.CharField("código", max_length=50)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    ubicacion_tipo = models.CharField(
        "tipo de ubicación", max_length=20, choices=UbicacionTipo.choices
    )
    lat = models.DecimalField(
        "latitud", max_digits=9, decimal_places=6, null=True, blank=True
    )
    long = models.DecimalField(
        "longitud", max_digits=9, decimal_places=6, null=True, blank=True
    )
    capacidad_puertos = models.PositiveIntegerField(
        "capacidad de puertos", null=True, blank=True
    )

    class Meta:
        verbose_name = "elemento de red"
        verbose_name_plural = "elementos de red"
        ordering = ["codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["obra", "codigo"], name="uniq_elemento_codigo_obra"
            )
        ]

    def __str__(self):
        return f"{self.codigo} ({self.get_tipo_display()})"


class Cable(models.Model):
    """Tramo de cable entre dos elementos de la red."""

    class TipoCable(models.TextChoices):
        EXTERIOR = "EXTERIOR", "Exterior"
        INTERIOR = "INTERIOR", "Interior"
        RISER = "RISER", "Riser"
        ADSS = "ADSS", "ADSS"
        DROP = "DROP", "Drop"
        MICRO = "MICRO", "Micro"

    class TipoFibra(models.TextChoices):
        SM_G652D = "SM_G652D", "SM G.652.D"
        SM_G657A1 = "SM_G657A1", "SM G.657.A1"
        SM_G657A2 = "SM_G657A2", "SM G.657.A2"
        MM_OM3 = "MM_OM3", "MM OM3"
        MM_OM4 = "MM_OM4", "MM OM4"

    obra = models.ForeignKey(
        Obra, verbose_name="obra", on_delete=models.CASCADE, related_name="cables"
    )
    elemento_a = models.ForeignKey(
        ElementoRed,
        verbose_name="elemento A",
        on_delete=models.PROTECT,
        related_name="cables_como_a",
    )
    elemento_b = models.ForeignKey(
        ElementoRed,
        verbose_name="elemento B",
        on_delete=models.PROTECT,
        related_name="cables_como_b",
    )
    codigo = models.CharField("código", max_length=50)
    tipo_cable = models.CharField("tipo de cable", max_length=20, choices=TipoCable.choices)
    tipo_fibra = models.CharField("tipo de fibra", max_length=20, choices=TipoFibra.choices)
    n_tubos = models.PositiveIntegerField("nº de tubos")
    fibras_por_tubo = models.PositiveIntegerField("fibras por tubo")
    longitud_m = models.DecimalField("longitud (m)", max_digits=9, decimal_places=2)

    class Meta:
        verbose_name = "cable"
        verbose_name_plural = "cables"
        ordering = ["codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["obra", "codigo"], name="uniq_cable_codigo_obra"
            ),
            models.CheckConstraint(
                condition=~Q(elemento_a=F("elemento_b")),
                name="chk_cable_extremos_distintos",
            ),
        ]

    @property
    def n_fibras(self):
        """Número total de fibras del cable."""
        return self.n_tubos * self.fibras_por_tubo

    def __str__(self):
        return f"{self.codigo} ({self.n_fibras}F)"


class PasoTubo(models.Model):
    """Tubo de un cable que atraviesa un elemento íntegro, sin abrirse."""

    elemento = models.ForeignKey(
        ElementoRed,
        verbose_name="elemento",
        on_delete=models.CASCADE,
        related_name="pasos_tubo",
    )
    cable = models.ForeignKey(
        Cable, verbose_name="cable", on_delete=models.CASCADE, related_name="pasos_tubo"
    )
    tubo = models.PositiveIntegerField("tubo")

    class Meta:
        verbose_name = "paso de tubo"
        verbose_name_plural = "pasos de tubo"
        constraints = [
            models.UniqueConstraint(
                fields=["elemento", "cable", "tubo"], name="uniq_paso_tubo"
            )
        ]

    def clean(self):
        super().clean()
        # I4 también aplica a pasos de tubo: el tubo debe existir en el cable.
        if self.cable_id and self.tubo and self.tubo > self.cable.n_tubos:
            raise ValidationError(
                {"tubo": f"El cable solo tiene {self.cable.n_tubos} tubos."}
            )

    def __str__(self):
        return f"{self.elemento.codigo} · {self.cable.codigo} · tubo {self.tubo}"


class Splitter(models.Model):
    """Splitter óptico instalado en un elemento (p. ej. una CTO)."""

    class Ratio(models.TextChoices):
        R1_2 = "1:2", "1:2"
        R1_4 = "1:4", "1:4"
        R1_8 = "1:8", "1:8"
        R1_16 = "1:16", "1:16"
        R1_32 = "1:32", "1:32"
        R1_64 = "1:64", "1:64"

    elemento = models.ForeignKey(
        ElementoRed,
        verbose_name="elemento",
        on_delete=models.CASCADE,
        related_name="splitters",
    )
    ratio = models.CharField("ratio", max_length=5, choices=Ratio.choices)
    cascada_de = models.ForeignKey(
        "self",
        verbose_name="en cascada de",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="splitters_cascada",
    )

    class Meta:
        verbose_name = "splitter"
        verbose_name_plural = "splitters"

    def __str__(self):
        return f"Splitter {self.ratio} @ {self.elemento.codigo}"


class Puerto(models.Model):
    """Puerto conectable de un elemento: fibra de cable, puerto de splitter,
    pigtail o reserva. Las fusiones/conexiones se hacen entre puertos."""

    class Tipo(models.TextChoices):
        FIBRA_CABLE = "FIBRA_CABLE", "Fibra de cable"
        PUERTO_SPLITTER_IN = "PUERTO_SPLITTER_IN", "Entrada de splitter"
        PUERTO_SPLITTER_OUT = "PUERTO_SPLITTER_OUT", "Salida de splitter"
        PIGTAIL = "PIGTAIL", "Pigtail"
        RESERVA = "RESERVA", "Reserva"

    elemento = models.ForeignKey(
        ElementoRed,
        verbose_name="elemento",
        on_delete=models.CASCADE,
        related_name="puertos",
    )
    tipo = models.CharField("tipo", max_length=20, choices=Tipo.choices)
    cable = models.ForeignKey(
        Cable,
        verbose_name="cable",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="puertos",
    )
    tubo = models.PositiveIntegerField("tubo", null=True, blank=True)
    fibra = models.PositiveIntegerField("fibra (dentro del tubo)", null=True, blank=True)
    splitter = models.ForeignKey(
        Splitter,
        verbose_name="splitter",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="puertos",
    )
    puerto = models.PositiveIntegerField("nº de puerto", null=True, blank=True)
    reservado_para = models.CharField("reservado para", max_length=150, blank=True)

    class Meta:
        verbose_name = "puerto"
        verbose_name_plural = "puertos"
        constraints = [
            # CHECKs por tipo (exigidos por el SPEC)
            models.CheckConstraint(
                condition=Q(tipo="FIBRA_CABLE", cable__isnull=False, tubo__isnull=False, fibra__isnull=False)
                | ~Q(tipo="FIBRA_CABLE"),
                name="chk_puerto_fibra_cable_completo",
            ),
            models.CheckConstraint(
                condition=Q(
                    tipo__in=["PUERTO_SPLITTER_IN", "PUERTO_SPLITTER_OUT"],
                    splitter__isnull=False,
                    puerto__isnull=False,
                )
                | ~Q(tipo__in=["PUERTO_SPLITTER_IN", "PUERTO_SPLITTER_OUT"]),
                name="chk_puerto_splitter_completo",
            ),
            # Unicidades parciales según el tipo de puerto
            models.UniqueConstraint(
                fields=["elemento", "cable", "tubo", "fibra"],
                condition=Q(tipo="FIBRA_CABLE"),
                name="uniq_puerto_fibra_cable",
            ),
            models.UniqueConstraint(
                fields=["splitter", "tipo", "puerto"],
                condition=Q(tipo__in=["PUERTO_SPLITTER_IN", "PUERTO_SPLITTER_OUT"]),
                name="uniq_puerto_splitter",
            ),
        ]

    def clean(self):
        super().clean()
        errores = {}
        if self.tipo == self.Tipo.FIBRA_CABLE:
            # I4: tubo/fibra dentro del rango del cable.
            if self.cable_id:
                if self.tubo is not None and self.tubo > self.cable.n_tubos:
                    errores["tubo"] = (
                        f"El cable {self.cable.codigo} solo tiene "
                        f"{self.cable.n_tubos} tubos."
                    )
                if self.fibra is not None and self.fibra > self.cable.fibras_por_tubo:
                    errores["fibra"] = (
                        f"El cable {self.cable.codigo} solo tiene "
                        f"{self.cable.fibras_por_tubo} fibras por tubo."
                    )
                # El cable debe terminar en este elemento.
                if self.cable_id and self.elemento_id and self.cable.elemento_a_id != self.elemento_id and self.cable.elemento_b_id != self.elemento_id:
                    errores["cable"] = "El cable no termina en este elemento."
        if errores:
            raise ValidationError(errores)

    def __str__(self):
        if self.tipo == self.Tipo.FIBRA_CABLE and self.cable_id:
            return (
                f"{self.elemento.codigo} · {self.cable.codigo} "
                f"T{self.tubo}/F{self.fibra}"
            )
        return f"{self.elemento.codigo} · {self.get_tipo_display()} {self.puerto or ''}".strip()


class Fusion(models.Model):
    """Fusión entre dos puertos de un mismo elemento.

    Concurrencia optimista: ``version`` se incrementa en cada guardado y
    ``save()`` lanza ``ValidationError`` si la versión en BD ha cambiado.
    """

    class Estado(models.TextChoices):
        EJECUTADA = "EJECUTADA", "Ejecutada"
        MEDIDA = "MEDIDA", "Medida"
        VALIDADA = "VALIDADA", "Validada"

    class Nivel(models.TextChoices):
        OK = "OK", "OK"
        WARNING = "WARNING", "Warning"
        FUERA = "FUERA", "Fuera de umbral"

    elemento = models.ForeignKey(
        ElementoRed,
        verbose_name="elemento",
        on_delete=models.CASCADE,
        related_name="fusiones",
    )
    puerto_a = models.ForeignKey(
        Puerto,
        verbose_name="puerto A",
        on_delete=models.PROTECT,
        related_name="fusiones_como_a",
    )
    puerto_b = models.ForeignKey(
        Puerto,
        verbose_name="puerto B",
        on_delete=models.PROTECT,
        related_name="fusiones_como_b",
    )
    perdida_db = models.DecimalField(
        "pérdida (dB)", max_digits=5, decimal_places=3, null=True, blank=True
    )
    bandeja = models.PositiveIntegerField("bandeja", null=True, blank=True)
    posicion = models.PositiveIntegerField("posición en bandeja", null=True, blank=True)
    estado = models.CharField(
        "estado", max_length=20, choices=Estado.choices, default=Estado.EJECUTADA
    )
    activa = models.BooleanField("activa", default=True)
    sustituida_por = models.ForeignKey(
        "self",
        verbose_name="sustituida por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sustituye_a",
    )
    version = models.PositiveIntegerField("versión", default=1)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="creada por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fusiones_creadas",
    )
    creado = models.DateTimeField("creado", auto_now_add=True)
    modificado = models.DateTimeField("modificado", auto_now=True)

    class Meta:
        verbose_name = "fusión"
        verbose_name_plural = "fusiones"
        constraints = [
            # I1: índices únicos parciales WHERE activa (un puerto, una fusión activa)
            models.UniqueConstraint(
                fields=["puerto_a"],
                condition=Q(activa=True),
                name="uniq_fusion_activa_puerto_a",
            ),
            models.UniqueConstraint(
                fields=["puerto_b"],
                condition=Q(activa=True),
                name="uniq_fusion_activa_puerto_b",
            ),
            # Una posición de bandeja, una fusión activa
            models.UniqueConstraint(
                fields=["elemento", "bandeja", "posicion"],
                condition=Q(activa=True, bandeja__isnull=False),
                name="uniq_fusion_activa_bandeja_posicion",
            ),
            # I3 a nivel de base de datos
            models.CheckConstraint(
                condition=Q(perdida_db__isnull=True)
                | Q(perdida_db__gte=0, perdida_db__lt=3),
                name="chk_fusion_perdida_rango",
            ),
        ]

    def clean(self):
        super().clean()
        errores = {}
        # I2: puerto_a != puerto_b y ambos del mismo elemento.
        if self.puerto_a_id and self.puerto_b_id:
            if self.puerto_a_id == self.puerto_b_id:
                errores["puerto_b"] = "puerto_a y puerto_b deben ser distintos."
            elif self.puerto_a.elemento_id != self.puerto_b.elemento_id:
                errores["__all__"] = "Ambos puertos deben pertenecer al mismo elemento."
            elif self.elemento_id and self.puerto_a.elemento_id != self.elemento_id:
                errores["elemento"] = (
                    "La fusión debe registrarse en el elemento de sus puertos."
                )
        # I3: pérdida >= 0 y < 3 dB.
        if self.perdida_db is not None and not (0 <= self.perdida_db < 3):
            errores["perdida_db"] = "La pérdida debe estar entre 0 y 3 dB."
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        # Concurrencia optimista: en actualizaciones se exige que la versión
        # en BD coincida con la del objeto; si no, otro proceso la modificó.
        if self.pk is not None:
            campos = {
                campo: getattr(self, campo) for campo in self._campos_editables()
            }
            # update() no dispara auto_now: se fija a mano.
            campos["modificado"] = timezone.now()
            actualizada = type(self).objects.filter(
                pk=self.pk, version=self.version
            ).update(version=self.version + 1, **campos)
            if not actualizada:
                raise ValidationError(
                    "La fusión fue modificada por otro usuario; recarga y reintenta."
                )
            self.version += 1
            return
        super().save(*args, **kwargs)

    def _campos_editables(self):
        """Campos que se persisten en un update (todos menos pk/version/fechas)."""
        excluir = {"id", "version", "creado", "modificado"}
        return [
            f.attname
            for f in self._meta.concrete_fields
            if f.attname not in excluir and f.name not in excluir
        ]

    @property
    def tipo_fibra_grupo(self):
        """'SM' o 'MM' según el tipo de fibra del cable del puerto A."""
        cable = getattr(self.puerto_a, "cable", None)
        if cable is None:
            return "SM"
        return "MM" if cable.tipo_fibra.startswith("MM") else "SM"

    @property
    def nivel(self):
        """Nivel de la fusión según los umbrales de la obra y el tipo de fibra.

        Devuelve ``None`` si la fusión no tiene pérdida medida.
        """
        if self.perdida_db is None:
            return None
        umbrales = self.elemento.obra.umbrales or UMBRALES_DEFECTO
        grupo = umbrales.get(self.tipo_fibra_grupo, umbrales.get("SM", {}))
        if self.perdida_db < grupo.get("ok", 0.05):
            return self.Nivel.OK
        if self.perdida_db < grupo.get("warn", 0.10):
            return self.Nivel.WARNING
        return self.Nivel.FUERA

    def __str__(self):
        return f"Fusión #{self.pk} @ {self.elemento.codigo}"


class Conexion(models.Model):
    """Conectorización entre dos puertos de una CTO preconectorizada.

    Igual que :class:`Fusion` pero sin pérdida ni bandeja/posición.
    """

    class Estado(models.TextChoices):
        EJECUTADA = "EJECUTADA", "Ejecutada"
        MEDIDA = "MEDIDA", "Medida"
        VALIDADA = "VALIDADA", "Validada"

    elemento = models.ForeignKey(
        ElementoRed,
        verbose_name="elemento",
        on_delete=models.CASCADE,
        related_name="conexiones",
    )
    puerto_a = models.ForeignKey(
        Puerto,
        verbose_name="puerto A",
        on_delete=models.PROTECT,
        related_name="conexiones_como_a",
    )
    puerto_b = models.ForeignKey(
        Puerto,
        verbose_name="puerto B",
        on_delete=models.PROTECT,
        related_name="conexiones_como_b",
    )
    estado = models.CharField(
        "estado", max_length=20, choices=Estado.choices, default=Estado.EJECUTADA
    )
    activa = models.BooleanField("activa", default=True)
    sustituida_por = models.ForeignKey(
        "self",
        verbose_name="sustituida por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sustituye_a",
    )
    version = models.PositiveIntegerField("versión", default=1)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="creada por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conexiones_creadas",
    )
    creado = models.DateTimeField("creado", auto_now_add=True)
    modificado = models.DateTimeField("modificado", auto_now=True)

    class Meta:
        verbose_name = "conexión"
        verbose_name_plural = "conexiones"
        constraints = [
            # I1: mismas unicidades parciales que Fusion
            models.UniqueConstraint(
                fields=["puerto_a"],
                condition=Q(activa=True),
                name="uniq_conexion_activa_puerto_a",
            ),
            models.UniqueConstraint(
                fields=["puerto_b"],
                condition=Q(activa=True),
                name="uniq_conexion_activa_puerto_b",
            ),
        ]

    def clean(self):
        super().clean()
        errores = {}
        # I2: puerto_a != puerto_b y ambos del mismo elemento.
        if self.puerto_a_id and self.puerto_b_id:
            if self.puerto_a_id == self.puerto_b_id:
                errores["puerto_b"] = "puerto_a y puerto_b deben ser distintos."
            elif self.puerto_a.elemento_id != self.puerto_b.elemento_id:
                errores["__all__"] = "Ambos puertos deben pertenecer al mismo elemento."
            elif self.elemento_id and self.puerto_a.elemento_id != self.elemento_id:
                errores["elemento"] = (
                    "La conexión debe registrarse en el elemento de sus puertos."
                )
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        # Concurrencia optimista, igual que en Fusion.
        if self.pk is not None:
            campos = {
                f.attname: getattr(self, f.attname)
                for f in self._meta.concrete_fields
                if f.attname not in {"id", "version", "creado", "modificado"}
            }
            campos["modificado"] = timezone.now()
            actualizada = type(self).objects.filter(
                pk=self.pk, version=self.version
            ).update(version=self.version + 1, **campos)
            if not actualizada:
                raise ValidationError(
                    "La conexión fue modificada por otro usuario; recarga y reintenta."
                )
            self.version += 1
            return
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Conexión #{self.pk} @ {self.elemento.codigo}"
