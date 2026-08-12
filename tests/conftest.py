"""Fixtures pytest compartidas: dos contratas con topología mínima cada una."""
import datetime
from decimal import Decimal

import pytest

from apps.accounts.models import Contrata, Trabajador, User
from apps.core.models import Cliente, EsquemaColor, PerfilOperadora
from apps.network.models import Cable, ElementoRed, Obra, Puerto

PASSWORD = "test-pass-1234"


@pytest.fixture
def contrata_a(db):
    return Contrata.objects.create(nombre="Contrata A", slug="contrata-a")


@pytest.fixture
def contrata_b(db):
    return Contrata.objects.create(nombre="Contrata B", slug="contrata-b")


def _crear_usuario(contrata, username):
    return User.objects.create_user(
        username=username, password=PASSWORD, contrata=contrata,
        rol=User.Rol.FUSIONADOR,
    )


@pytest.fixture
def user_a(contrata_a):
    return _crear_usuario(contrata_a, "user-a")


@pytest.fixture
def user_b(contrata_b):
    return _crear_usuario(contrata_b, "user-b")


def _crear_topologia(contrata):
    """Crea obra + empalme + 2 cables + puertos de prueba para una contrata."""
    esquema = EsquemaColor.objects.create(
        contrata=None, nombre="DIN VDE 0888",
        ambito=EsquemaColor.Ambito.DIN_VDE0888,
        colores=[f"c{i}" for i in range(1, 13)],
    )
    cliente = Cliente.objects.create(contrata=contrata, nombre=f"Op {contrata.slug}")
    perfil = PerfilOperadora.objects.create(
        cliente=cliente, nombre="Perfil", esquema_color=esquema,
        umbrales={"SM": {"ok": 0.05, "warn": 0.10},
                  "MM": {"ok": 0.10, "warn": 0.20}},
    )
    obra = Obra.objects.create(
        contrata=contrata, cliente=cliente, perfil_operadora=perfil,
        codigo=f"OB-{contrata.slug}", arquitectura=Obra.Arquitectura.GPON_CASCADA,
        umbrales=perfil.umbrales,
    )
    emp1 = ElementoRed.objects.create(
        obra=obra, tipo=ElementoRed.Tipo.EMPALME, codigo="EMP-01",
        ubicacion_tipo=ElementoRed.UbicacionTipo.ARQUETA,
    )
    emp2 = ElementoRed.objects.create(
        obra=obra, tipo=ElementoRed.Tipo.EMPALME, codigo="EMP-02",
        ubicacion_tipo=ElementoRed.UbicacionTipo.ARQUETA,
    )
    cable1 = Cable.objects.create(
        obra=obra, elemento_a=emp1, elemento_b=emp2, codigo="C-01",
        tipo_cable=Cable.TipoCable.EXTERIOR, tipo_fibra=Cable.TipoFibra.SM_G652D,
        n_tubos=2, fibras_por_tubo=12, longitud_m=Decimal("100.00"),
    )
    cable2 = Cable.objects.create(
        obra=obra, elemento_a=emp2, elemento_b=emp1, codigo="C-02",
        tipo_cable=Cable.TipoCable.MICRO, tipo_fibra=Cable.TipoFibra.SM_G657A2,
        n_tubos=2, fibras_por_tubo=12, longitud_m=Decimal("80.00"),
    )

    def puerto(elemento, cable, tubo, fibra):
        p = Puerto(elemento=elemento, tipo=Puerto.Tipo.FIBRA_CABLE,
                   cable=cable, tubo=tubo, fibra=fibra)
        p.full_clean()
        p.save()
        return p

    return {
        "obra": obra, "emp1": emp1, "emp2": emp2,
        "cable1": cable1, "cable2": cable2, "puerto": puerto,
        "trabajador": Trabajador.objects.create(
            contrata=contrata, nombre=f"Trab {contrata.slug}"
        ),
        "hoy": datetime.date(2026, 2, 1),
    }


@pytest.fixture
def topo_a(contrata_a):
    return _crear_topologia(contrata_a)


@pytest.fixture
def topo_b(contrata_b):
    return _crear_topologia(contrata_b)


@pytest.fixture
def api_a(user_a):
    """APIClient autenticado por sesión como usuario de la contrata A."""
    from rest_framework.test import APIClient

    cliente = APIClient()
    cliente.force_authenticate(user=user_a)
    return cliente


@pytest.fixture
def api_b(user_b):
    from rest_framework.test import APIClient

    cliente = APIClient()
    cliente.force_authenticate(user=user_b)
    return cliente
