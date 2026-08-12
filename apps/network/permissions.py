"""Permisos de la API: aislamiento multi-tenant por contrata."""
from rest_framework.permissions import BasePermission


def contrata_de(obj):
    """Devuelve la contrata (tenant) a la que pertenece un objeto, o None."""
    if obj is None:
        return None
    if hasattr(obj, "contrata_id"):
        return obj.contrata_id
    for ruta in ("obra", "elemento", "cable", "tarifa", "cliente"):
        padre = getattr(obj, ruta, None)
        if padre is None:
            continue
        if hasattr(padre, "contrata_id"):
            return padre.contrata_id
        # un nivel más (p. ej. Fusion -> elemento -> obra -> contrata)
        obra = getattr(padre, "obra", None)
        if obra is not None and hasattr(obra, "contrata_id"):
            return obra.contrata_id
        if hasattr(padre, "elemento", None) and padre.elemento is not None:
            obra = getattr(padre.elemento, "obra", None)
            if obra is not None and hasattr(obra, "contrata_id"):
                return obra.contrata_id
    # Fusion/Conexion: elemento -> obra -> contrata
    elemento = getattr(obj, "elemento", None)
    if elemento is not None:
        obra = getattr(elemento, "obra", None)
        if obra is not None:
            return getattr(obra, "contrata_id", None)
    return None


class IsSameContrata(BasePermission):
    """Solo permite acceder a objetos de la propia contrata del usuario.

    El superadministrador (is_superuser) tiene acceso total. Los viewsets
    además filtran sus querysets por ``request.user.contrata``, por lo que
    el objeto de otra contrata ni siquiera se resuelve (404); esta
    comprobación es la segunda línea de defensa (403).
    """

    message = "No tienes acceso a objetos de otra contrata."

    def has_permission(self, request, view):
        usuario = request.user
        if not usuario or not usuario.is_authenticated:
            return False
        # Sin contrata solo puede operar el superadmin.
        return usuario.is_superuser or usuario.contrata_id is not None

    def has_object_permission(self, request, view, obj):
        usuario = request.user
        if usuario.is_superuser:
            return True
        return contrata_de(obj) == usuario.contrata_id
