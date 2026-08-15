"""Tests de la API: aislamiento multi-tenant y endpoints resumen/matriz."""
from decimal import Decimal

import pytest

from apps.network.models import Conexion, Fusion, Puerto


def _fusion(elemento, pa, pb, **kwargs):
    fusion = Fusion(elemento=elemento, puerto_a=pa, puerto_b=pb, **kwargs)
    fusion.full_clean()
    fusion.save()
    return fusion


@pytest.mark.django_db
class TestAislamientoMultiTenant:
    def test_lista_obras_no_muestra_las_de_otra_contrata(
        self, api_a, api_b, topo_a, topo_b
    ):
        resp_a = api_a.get("/api/obras/")
        resp_b = api_b.get("/api/obras/")
        assert resp_a.status_code == 200 and resp_b.status_code == 200
        codigos_a = {o["codigo"] for o in resp_a.json()}
        codigos_b = {o["codigo"] for o in resp_b.json()}
        assert topo_a["obra"].codigo in codigos_a
        assert topo_a["obra"].codigo not in codigos_b

    def test_detalle_obra_de_otra_contrata_da_404(
        self, api_b, topo_a, topo_b
    ):
        resp = api_b.get(f"/api/obras/{topo_a['obra'].id}/")
        assert resp.status_code == 404

    def test_modificar_obra_de_otra_contrata_da_404(
        self, api_b, topo_a, topo_b
    ):
        resp = api_b.patch(
            f"/api/obras/{topo_a['obra'].id}/", {"direccion": "X"}, format="json"
        )
        assert resp.status_code == 404

    def test_lista_elementos_filtrada_por_contrata(
        self, api_a, api_b, topo_a, topo_b
    ):
        resp_b = api_b.get("/api/elementos/")
        assert resp_b.status_code == 200
        codigos = {e["codigo"] for e in resp_b.json()}
        assert "EMP-01" in codigos  # el suyo
        ids_b = {e["id"] for e in resp_b.json()}
        assert topo_a["emp1"].id not in ids_b

    def test_detalle_fusion_de_otra_contrata_da_404(
        self, api_b, topo_a, topo_b
    ):
        emp = topo_a["emp1"]
        pa = topo_a["puerto"](emp, topo_a["cable1"], 1, 1)
        pb = topo_a["puerto"](emp, topo_a["cable1"], 1, 2)
        fusion = _fusion(emp, pa, pb)
        assert api_b.get(f"/api/fusiones/{fusion.id}/").status_code == 404

    def test_sin_autenticar_da_403(self, topo_a):
        from rest_framework.test import APIClient

        resp = APIClient().get("/api/obras/")
        assert resp.status_code == 403


@pytest.mark.django_db
class TestResumenYMatriz:
    def _montar_fusiones(self, topo):
        """3 fusiones entre cable1 y cable2 con pérdidas OK/WARNING/FUERA."""
        emp = topo["emp1"]
        datos = []
        for i, perdida in enumerate(["0.030", "0.070", "0.150"], start=1):
            pa = topo["puerto"](emp, topo["cable1"], 1, i)
            pb = topo["puerto"](emp, topo["cable2"], 1, i)
            datos.append(_fusion(
                emp, pa, pb, perdida_db=Decimal(perdida),
                estado=Fusion.Estado.MEDIDA,
            ))
        return datos

    def test_resumen_200_y_shape(self, api_a, topo_a):
        self._montar_fusiones(topo_a)
        emp = topo_a["emp1"]
        Conexion.objects.create(
            elemento=emp,
            puerto_a=topo_a["puerto"](emp, topo_a["cable1"], 2, 1),
            puerto_b=topo_a["puerto"](emp, topo_a["cable2"], 2, 1),
        )
        resp = api_a.get(f"/api/elementos/{emp.id}/resumen/")
        assert resp.status_code == 200
        datos = resp.json()
        assert datos["elemento"] == emp.id
        assert datos["fusiones_activas"] == 3
        assert datos["por_estado"] == {"MEDIDA": 3}
        assert datos["por_nivel"] == {"OK": 1, "WARNING": 1, "FUERA": 1}
        assert datos["conexiones_activas"] == 1

    def test_matriz_200_y_shape_sparse(self, api_a, topo_a):
        self._montar_fusiones(topo_a)
        emp = topo_a["emp1"]
        resp = api_a.get(
            f"/api/elementos/{emp.id}/matriz/",
            {"cable_a": topo_a["cable1"].id, "cable_b": topo_a["cable2"].id},
        )
        assert resp.status_code == 200
        datos = resp.json()
        assert datos["elemento"] == emp.id
        assert len(datos["filas"]) == 3
        fila = datos["filas"][0]
        assert set(fila) >= {
            "fusion_id", "tubo_a", "fibra_a", "tubo_b", "fibra_b",
            "perdida_db", "nivel", "estado",
        }
        niveles = {f["nivel"] for f in datos["filas"]}
        assert niveles == {"OK", "WARNING", "FUERA"}

    def test_matriz_orientacion_invertida(self, api_a, topo_a):
        self._montar_fusiones(topo_a)
        emp = topo_a["emp1"]
        resp = api_a.get(
            f"/api/elementos/{emp.id}/matriz/",
            {"cable_a": topo_a["cable2"].id, "cable_b": topo_a["cable1"].id},
        )
        assert resp.status_code == 200
        assert len(resp.json()["filas"]) == 3

    def test_matriz_sin_parametros_da_400(self, api_a, topo_a):
        resp = api_a.get(f"/api/elementos/{topo_a['emp1'].id}/matriz/")
        assert resp.status_code == 400

    def test_api_docs_accesible(self, api_a):
        assert api_a.get("/api/docs/").status_code == 200
        assert api_a.get("/api/schema/").status_code == 200


@pytest.mark.django_db
class TestAuthSPA:
    """Endpoints de autenticación por sesión para el frontend React."""

    def test_login_ok_devuelve_usuario_y_sesion(self, user_a, contrata_a):
        from rest_framework.test import APIClient

        cliente = APIClient()
        resp = cliente.post(
            "/api/auth/login/",
            {"username": "user-a", "password": "test-pass-1234"},
            format="json",
        )
        assert resp.status_code == 200
        datos = resp.json()
        assert datos["username"] == "user-a"
        assert datos["rol"] == "FUSIONADOR"
        assert datos["contrata"] == "Contrata A"
        # La sesión queda establecida: /me/ responde 200 con el mismo usuario
        assert cliente.get("/api/auth/me/").json()["username"] == "user-a"

    def test_login_credenciales_incorrectas_da_401(self, user_a):
        from rest_framework.test import APIClient

        cliente = APIClient()
        resp = cliente.post(
            "/api/auth/login/",
            {"username": "user-a", "password": "mal"},
            format="json",
        )
        assert resp.status_code == 401

    def test_me_sin_sesion_da_401(self, db):
        from rest_framework.test import APIClient

        assert APIClient().get("/api/auth/me/").status_code == 401

    def test_me_con_sesion_da_200(self, user_a):
        from rest_framework.test import APIClient

        cliente = APIClient()
        cliente.login(username="user-a", password="test-pass-1234")
        resp = cliente.get("/api/auth/me/")
        assert resp.status_code == 200
        assert resp.json()["username"] == "user-a"
