"""Vistas de autenticación SPA para el frontend React de FiberDoc.

Autenticación por sesión de Django (decisión de la fase 1: no JWT).
El login está decorado con ``ensure_csrf_cookie``: el SPA lee la cookie
``csrftoken`` y la reenvía en la cabecera ``X-CSRFToken`` de los POST.
"""
import json

from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST


def _usuario_json(user):
    return {
        "id": user.id,
        "username": user.username,
        "rol": user.rol,
        "contrata": user.contrata.nombre if user.contrata_id else None,
    }


@ensure_csrf_cookie
@require_POST
def api_login(request):
    """Login SPA: POST JSON {username, password} → 200 usuario o 401."""
    try:
        datos = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Cuerpo JSON inválido."}, status=400)
    user = authenticate(
        request,
        username=datos.get("username", ""),
        password=datos.get("password", ""),
    )
    if user is None or not user.is_active:
        return JsonResponse(
            {"detail": "Usuario o contraseña incorrectos."}, status=401
        )
    login(request, user)
    return JsonResponse(_usuario_json(user))


@require_POST
def api_logout(request):
    """Cierra la sesión actual (204 aunque no hubiera sesión)."""
    logout(request)
    return HttpResponse(status=204)


@ensure_csrf_cookie
@require_GET
def api_me(request):
    """Devuelve el usuario autenticado o 401 si no hay sesión."""
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"detail": "No autenticado."}, status=401)
    return JsonResponse(_usuario_json(user))
