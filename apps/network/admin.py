"""Admin de la app network: listados con filtros por contrata y obra."""
from django.contrib import admin

from .models import (
    Cable,
    Conexion,
    ElementoRed,
    Fusion,
    Obra,
    OrdenTrabajo,
    PasoTubo,
    Puerto,
    Splitter,
)


class ElementoInline(admin.TabularInline):
    model = ElementoRed
    extra = 0
    show_change_link = True


@admin.register(Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = ("codigo", "cliente", "contrata", "estado", "arquitectura", "creado")
    list_filter = ("contrata", "cliente", "estado", "arquitectura")
    search_fields = ("codigo", "direccion")
    inlines = [ElementoInline]


@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = ("obra", "tipo", "trabajador", "fecha", "estado")
    list_filter = ("obra__contrata", "obra", "tipo", "estado")
    date_hierarchy = "fecha"


@admin.register(ElementoRed)
class ElementoRedAdmin(admin.ModelAdmin):
    list_display = ("codigo", "tipo", "obra", "ubicacion_tipo", "capacidad_puertos")
    list_filter = ("obra__contrata", "obra", "tipo", "ubicacion_tipo")
    search_fields = ("codigo", "direccion")


@admin.register(Cable)
class CableAdmin(admin.ModelAdmin):
    list_display = ("codigo", "obra", "elemento_a", "elemento_b", "tipo_fibra", "n_fibras", "longitud_m")
    list_filter = ("obra__contrata", "obra", "tipo_cable", "tipo_fibra")
    search_fields = ("codigo",)


@admin.register(PasoTubo)
class PasoTuboAdmin(admin.ModelAdmin):
    list_display = ("elemento", "cable", "tubo")
    list_filter = ("elemento__obra__contrata", "elemento__obra", "elemento")


@admin.register(Splitter)
class SplitterAdmin(admin.ModelAdmin):
    list_display = ("elemento", "ratio", "cascada_de")
    list_filter = ("elemento__obra__contrata", "elemento__obra", "ratio")


@admin.register(Puerto)
class PuertoAdmin(admin.ModelAdmin):
    list_display = ("elemento", "tipo", "cable", "tubo", "fibra", "splitter", "puerto")
    list_filter = ("elemento__obra__contrata", "elemento__obra", "elemento", "tipo")
    search_fields = ("elemento__codigo", "cable__codigo")


@admin.register(Fusion)
class FusionAdmin(admin.ModelAdmin):
    list_display = ("id", "elemento", "puerto_a", "puerto_b", "perdida_db", "estado", "activa", "version")
    list_filter = ("elemento__obra__contrata", "elemento__obra", "elemento", "estado", "activa")
    readonly_fields = ("version", "creado", "modificado")


@admin.register(Conexion)
class ConexionAdmin(admin.ModelAdmin):
    list_display = ("id", "elemento", "puerto_a", "puerto_b", "estado", "activa", "version")
    list_filter = ("elemento__obra__contrata", "elemento__obra", "elemento", "estado", "activa")
    readonly_fields = ("version", "creado", "modificado")
