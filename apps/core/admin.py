"""Admin de la app core."""
from django.contrib import admin

from .models import Cliente, EsquemaColor, PerfilOperadora, TarifaItem, TarifaUO


@admin.register(EsquemaColor)
class EsquemaColorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ambito", "contrata")
    list_filter = ("ambito", "contrata")
    search_fields = ("nombre",)


class PerfilOperadoraInline(admin.StackedInline):
    model = PerfilOperadora
    extra = 0


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "contrata", "contacto")
    list_filter = ("contrata",)
    search_fields = ("nombre",)
    inlines = [PerfilOperadoraInline]


@admin.register(PerfilOperadora)
class PerfilOperadoraAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cliente", "arquitectura", "esquema_color")
    list_filter = ("cliente__contrata", "arquitectura")


class TarifaItemInline(admin.TabularInline):
    model = TarifaItem
    extra = 1


@admin.register(TarifaUO)
class TarifaUOAdmin(admin.ModelAdmin):
    list_display = ("codigo", "cliente", "vigente")
    list_filter = ("cliente__contrata", "cliente", "vigente")
    inlines = [TarifaItemInline]
