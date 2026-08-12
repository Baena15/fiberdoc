"""Admin de la app accounts."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Contrata, Trabajador, User


@admin.register(Contrata)
class ContrataAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug", "cif", "activa", "creado")
    list_filter = ("activa",)
    search_fields = ("nombre", "slug", "cif")
    prepopulated_fields = {"slug": ("nombre",)}


@admin.register(User)
class FiberDocUserAdmin(UserAdmin):
    list_display = ("username", "email", "rol", "contrata", "is_staff")
    list_filter = ("rol", "contrata", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("FiberDoc", {"fields": ("contrata", "rol")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("FiberDoc", {"fields": ("contrata", "rol")}),
    )


@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cuadrilla", "contrata", "user", "activo")
    list_filter = ("contrata", "activo", "cuadrilla")
    search_fields = ("nombre",)
