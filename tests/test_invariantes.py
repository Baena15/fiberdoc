"""Tests de los invariantes de negocio I1-I4 y de la propiedad `nivel`."""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.network.models import Fusion, Puerto


def _fusion(elemento, pa, pb, **kwargs):
    fusion = Fusion(elemento=elemento, puerto_a=pa, puerto_b=pb, **kwargs)
    fusion.full_clean()
    fusion.save()
    return fusion


@pytest.mark.django_db
class TestI1PuertoUnaFusionActiva:
    def test_segunda_fusion_activa_en_mismo_puerto_falla(self, topo_a):
        emp = topo_a["emp1"]
        pa = topo_a["puerto"](emp, topo_a["cable1"], 1, 1)
        pb = topo_a["puerto"](emp, topo_a["cable1"], 1, 2)
        pc = topo_a["puerto"](emp, topo_a["cable1"], 1, 3)
        _fusion(emp, pa, pb)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                # Sin full_clean: el índice parcial WHERE activa lo impide en BD.
                Fusion.objects.create(elemento=emp, puerto_a=pa, puerto_b=pc)

    def test_fusion_inactiva_libera_el_puerto(self, topo_a):
        emp = topo_a["emp1"]
        pa = topo_a["puerto"](emp, topo_a["cable1"], 1, 1)
        pb = topo_a["puerto"](emp, topo_a["cable1"], 1, 2)
        pc = topo_a["puerto"](emp, topo_a["cable1"], 1, 3)
        vieja = _fusion(emp, pa, pb)
        vieja.activa = False
        vieja.save()
        nueva = _fusion(emp, pa, pc)  # no debe fallar
        vieja.sustituida_por = nueva
        vieja.save()
        assert nueva.activa

    def test_bandeja_posicion_unica_si_activa(self, topo_a):
        emp = topo_a["emp1"]
        pa = topo_a["puerto"](emp, topo_a["cable1"], 1, 1)
        pb = topo_a["puerto"](emp, topo_a["cable1"], 1, 2)
        pc = topo_a["puerto"](emp, topo_a["cable1"], 1, 3)
        pd = topo_a["puerto"](emp, topo_a["cable1"], 1, 4)
        _fusion(emp, pa, pb, bandeja=1, posicion=1)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Fusion.objects.create(
                    elemento=emp, puerto_a=pc, puerto_b=pd, bandeja=1, posicion=1
                )


@pytest.mark.django_db
class TestI2MismoElemento:
    def test_puertos_iguales_falla(self, topo_a):
        emp = topo_a["emp1"]
        pa = topo_a["puerto"](emp, topo_a["cable1"], 1, 1)
        fusion = Fusion(elemento=emp, puerto_a=pa, puerto_b=pa)
        with pytest.raises(ValidationError):
            fusion.full_clean()

    def test_puertos_de_elementos_distintos_falla(self, topo_a):
        pa = topo_a["puerto"](topo_a["emp1"], topo_a["cable1"], 1, 1)
        pb = topo_a["puerto"](topo_a["emp2"], topo_a["cable1"], 1, 2)
        fusion = Fusion(elemento=topo_a["emp1"], puerto_a=pa, puerto_b=pb)
        with pytest.raises(ValidationError):
            fusion.full_clean()

    def test_puerto_splitter_en_conexion_ok(self, topo_a):
        # Sanity check: una fusión válida pasa la validación.
        emp = topo_a["emp1"]
        pa = topo_a["puerto"](emp, topo_a["cable1"], 1, 1)
        pb = topo_a["puerto"](emp, topo_a["cable2"], 1, 1)
        _fusion(emp, pa, pb)


@pytest.mark.django_db
class TestI3PerdidaRango:
    @pytest.mark.parametrize("perdida", ["-0.01", "3.00", "3.5"])
    def test_perdida_fuera_de_rango_falla(self, topo_a, perdida):
        emp = topo_a["emp1"]
        pa = topo_a["puerto"](emp, topo_a["cable1"], 1, 1)
        pb = topo_a["puerto"](emp, topo_a["cable1"], 1, 2)
        fusion = Fusion(
            elemento=emp, puerto_a=pa, puerto_b=pb,
            perdida_db=Decimal(perdida),
        )
        with pytest.raises(ValidationError):
            fusion.full_clean()

    def test_perdida_valida_y_nula_ok(self, topo_a):
        emp = topo_a["emp1"]
        pa = topo_a["puerto"](emp, topo_a["cable1"], 1, 1)
        pb = topo_a["puerto"](emp, topo_a["cable1"], 1, 2)
        _fusion(emp, pa, pb, perdida_db=Decimal("0.049"))
        pc = topo_a["puerto"](emp, topo_a["cable1"], 1, 3)
        pd = topo_a["puerto"](emp, topo_a["cable1"], 1, 4)
        _fusion(emp, pc, pd, perdida_db=None)


@pytest.mark.django_db
class TestI4TuboFibraEnRango:
    def test_tubo_fuera_de_rango_falla(self, topo_a):
        p = Puerto(
            elemento=topo_a["emp1"], tipo=Puerto.Tipo.FIBRA_CABLE,
            cable=topo_a["cable1"], tubo=99, fibra=1,
        )
        with pytest.raises(ValidationError):
            p.full_clean()

    def test_fibra_fuera_de_rango_falla(self, topo_a):
        p = Puerto(
            elemento=topo_a["emp1"], tipo=Puerto.Tipo.FIBRA_CABLE,
            cable=topo_a["cable1"], tubo=1, fibra=13,
        )
        with pytest.raises(ValidationError):
            p.full_clean()

    def test_cable_no_termina_en_elemento_falla(self, topo_a):
        # cable2 va de emp2 a emp1; creamos un tercer elemento ajeno al cable
        from apps.network.models import ElementoRed

        emp3 = ElementoRed.objects.create(
            obra=topo_a["obra"], tipo=ElementoRed.Tipo.CTO, codigo="CTO-99",
            ubicacion_tipo=ElementoRed.UbicacionTipo.AEREO_POSTE,
        )
        p = Puerto(
            elemento=emp3, tipo=Puerto.Tipo.FIBRA_CABLE,
            cable=topo_a["cable1"], tubo=1, fibra=1,
        )
        with pytest.raises(ValidationError):
            p.full_clean()


@pytest.mark.django_db
class TestNivelFusion:
    @pytest.mark.parametrize(
        "perdida, esperado",
        [("0.030", Fusion.Nivel.OK), ("0.070", Fusion.Nivel.WARNING),
         ("0.150", Fusion.Nivel.FUERA)],
    )
    def test_nivel_segun_umbrales_sm(self, topo_a, perdida, esperado):
        emp = topo_a["emp1"]
        pa = topo_a["puerto"](emp, topo_a["cable1"], 1, 1)
        pb = topo_a["puerto"](emp, topo_a["cable1"], 1, 2)
        fusion = _fusion(emp, pa, pb, perdida_db=Decimal(perdida))
        assert fusion.nivel == esperado

    def test_nivel_none_sin_perdida(self, topo_a):
        emp = topo_a["emp1"]
        pa = topo_a["puerto"](emp, topo_a["cable1"], 1, 1)
        pb = topo_a["puerto"](emp, topo_a["cable1"], 1, 2)
        fusion = _fusion(emp, pa, pb)
        assert fusion.nivel is None
