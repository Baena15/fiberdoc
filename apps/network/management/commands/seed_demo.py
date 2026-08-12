"""Management command ``seed_demo``: datos de demostración deterministas.

Genera (con ``random.seed(42)`` para reproducibilidad):
- Contrata "FibraSur Instalaciones" con 3 usuarios (admin/capataz/fusionador).
- Esquemas de color globales DIN VDE 0888 y TIA-568.
- Cliente operadora "NorteNet" con PerfilOperadora y tarifa con 6 ítems.
- Obra OB-2026-014: 1 ODF, 3 empalmes, 4 CTOs (splitters 1:4 -> 1:8 en
  cascada), cable troncal 144F y distribución 24F, ~150 fusiones
  (85 % OK / 12 % WARNING / 3 % FUERA), 2 de ellas subsanadas, y pasos
  de tubo en EMPALME-01.
"""
import random
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Contrata, Trabajador, User
from apps.core.models import (
    Cliente,
    EsquemaColor,
    PerfilOperadora,
    TarifaItem,
    TarifaUO,
)
from apps.network.models import (
    Cable,
    ElementoRed,
    Fusion,
    Obra,
    OrdenTrabajo,
    PasoTubo,
    Puerto,
    Splitter,
)

PASSWORD_DEMO = "FibraSur-demo-2026"

COLORES_DIN = [
    "rojo", "verde", "azul", "amarillo", "blanco", "gris",
    "marrón", "violeta", "turquesa", "negro", "naranja", "rosa",
]
COLORES_TIA = [
    "azul", "naranja", "verde", "marrón", "gris", "blanco",
    "rojo", "negro", "amarillo", "violeta", "rosa", "turquesa",
]


class Command(BaseCommand):
    help = "Crea los datos de demostración de FiberDoc (idempotente)."

    @transaction.atomic
    def handle(self, *args, **opciones):
        random.seed(42)  # reproducibilidad exigida por el SPEC

        if Contrata.objects.filter(slug="fibrasur").exists():
            self.stdout.write(self.style.WARNING(
                "La contrata 'fibrasur' ya existe; no se duplica el seed."
            ))
            return

        contrata = Contrata.objects.create(
            nombre="FibraSur Instalaciones", slug="fibrasur", cif="B-41123456"
        )

        # --- Usuarios demo (password documentada en el README) ---
        usuarios = {}
        for nombre, rol in (
            ("admin", User.Rol.ADMIN_CONTRATA),
            ("capataz", User.Rol.CAPATAZ),
            ("fusionador", User.Rol.FUSIONADOR),
        ):
            usuarios[nombre] = User.objects.create_user(
                username=nombre,
                password=PASSWORD_DEMO,
                contrata=contrata,
                rol=rol,
                is_staff=(rol == User.Rol.ADMIN_CONTRATA),
            )
        fusionador = Trabajador.objects.create(
            contrata=contrata,
            user=usuarios["fusionador"],
            nombre="Manuel Reyes (fusionador)",
            cuadrilla="CU-01",
        )
        capataz = Trabajador.objects.create(
            contrata=contrata,
            user=usuarios["capataz"],
            nombre="Lucía Ortega (capataz)",
            cuadrilla="CU-01",
        )

        # --- Esquemas de color globales ---
        din = EsquemaColor.objects.create(
            contrata=None, nombre="DIN VDE 0888",
            ambito=EsquemaColor.Ambito.DIN_VDE0888, colores=COLORES_DIN,
        )
        EsquemaColor.objects.create(
            contrata=None, nombre="TIA-568",
            ambito=EsquemaColor.Ambito.TIA_568, colores=COLORES_TIA,
        )

        # --- Cliente operadora y su perfil ---
        nortenet = Cliente.objects.create(
            contrata=contrata, nombre="NorteNet", contacto="ops@nortenet.example"
        )
        perfil = PerfilOperadora.objects.create(
            cliente=nortenet,
            nombre="Perfil estándar FTTH",
            umbrales={"SM": {"ok": 0.05, "warn": 0.10},
                      "MM": {"ok": 0.10, "warn": 0.20}},
            potencia_min_dbm=Decimal("-22.00"),
            potencia_max_dbm=Decimal("-8.00"),
            esquema_color=din,
            arquitectura=PerfilOperadora.Arquitectura.GPON_CASCADA,
            notas="Umbrales de fusión según especificación NorteNet 2026.",
        )

        # --- Tarifa con 6 ítems ---
        tarifa = TarifaUO.objects.create(
            cliente=nortenet, codigo="TAR-2026-NN",
            descripcion="Tarifa unidades de obra NorteNet 2026",
        )
        items = [
            ("FUS-EMPALME", "Fusión en empalme", "4.50", "fusión"),
            ("MONT-CTO-16", "Montaje de CTO 16 puertos", "38.00", "ud"),
            ("M-TENDIDO", "Tendido de cable", "0.85", "m"),
            ("MONT-SPLITTER", "Montaje de splitter", "12.00", "ud"),
            ("MED-OTDR", "Medición OTDR por fibra", "6.00", "fibra"),
            ("CONEX-CTO", "Conectorizado en CTO", "2.10", "conexión"),
        ]
        for codigo, desc, precio, unidad in items:
            TarifaItem.objects.create(
                tarifa=tarifa, codigo=codigo, descripcion=desc,
                precio=Decimal(precio), unidad=unidad,
            )

        # --- Obra y elementos ---
        obra = Obra.objects.create(
            contrata=contrata,
            cliente=nortenet,
            perfil_operadora=perfil,
            codigo="OB-2026-014",
            direccion="Urbanización Los Pinos, s/n",
            ubicacion="Dos Hermanas (Sevilla)",
            arquitectura=Obra.Arquitectura.GPON_CASCADA,
            estado=Obra.Estado.EN_CURSO,
            umbrales=perfil.umbrales,
            requiere_otdr=True,
        )

        odf = ElementoRed.objects.create(
            obra=obra, tipo=ElementoRed.Tipo.ODF, codigo="ODF-01",
            direccion="Centro NorteNet Sevilla Este",
            ubicacion_tipo=ElementoRed.UbicacionTipo.CENTRO_ODF,
            capacidad_puertos=288,
        )
        empalmes = [
            ElementoRed.objects.create(
                obra=obra, tipo=ElementoRed.Tipo.EMPALME,
                codigo=f"EMPALME-0{i}",
                direccion=f"Arqueta A-{i:02d}, Calle de los Pinos",
                ubicacion_tipo=ElementoRed.UbicacionTipo.ARQUETA,
                capacidad_puertos=144,
            )
            for i in range(1, 4)
        ]
        ctos = [
            ElementoRed.objects.create(
                obra=obra, tipo=ElementoRed.Tipo.CTO, codigo=f"CTO-0{i}",
                direccion=f"Fachada bloque {i}, Urb. Los Pinos",
                ubicacion_tipo=ElementoRed.UbicacionTipo.AEREO_FACHADA,
                capacidad_puertos=16,
            )
            for i in range(1, 5)
        ]

        # --- Splitters 1:4 -> 1:8 en cascada en cada CTO ---
        for cto in ctos:
            primario = Splitter.objects.create(
                elemento=cto, ratio=Splitter.Ratio.R1_4
            )
            for _ in range(2):
                Splitter.objects.create(
                    elemento=cto, ratio=Splitter.Ratio.R1_8, cascada_de=primario
                )

        # --- Cables: troncal 144F y distribución 24F ---
        troncal = Cable.objects.create(
            obra=obra, elemento_a=odf, elemento_b=empalmes[0],
            codigo="TRONCAL-01", tipo_cable=Cable.TipoCable.EXTERIOR,
            tipo_fibra=Cable.TipoFibra.SM_G652D,
            n_tubos=12, fibras_por_tubo=12, longitud_m=Decimal("2450.00"),
        )
        dist_01 = Cable.objects.create(
            obra=obra, elemento_a=empalmes[0], elemento_b=empalmes[1],
            codigo="DIST-01", tipo_cable=Cable.TipoCable.MICRO,
            tipo_fibra=Cable.TipoFibra.SM_G657A2,
            n_tubos=2, fibras_por_tubo=12, longitud_m=Decimal("610.00"),
        )
        dist_02 = Cable.objects.create(
            obra=obra, elemento_a=empalmes[1], elemento_b=empalmes[2],
            codigo="DIST-02", tipo_cable=Cable.TipoCable.MICRO,
            tipo_fibra=Cable.TipoFibra.SM_G657A2,
            n_tubos=2, fibras_por_tubo=12, longitud_m=Decimal("430.00"),
        )
        dist_cto = [
            Cable.objects.create(
                obra=obra,
                elemento_a=empalmes[2] if i < 2 else empalmes[1],
                elemento_b=ctos[i],
                codigo=f"DIST-0{3 + i}", tipo_cable=Cable.TipoCable.DROP,
                tipo_fibra=Cable.TipoFibra.SM_G657A2,
                n_tubos=2, fibras_por_tubo=12, longitud_m=Decimal("120.00"),
            )
            for i in range(4)
        ]

        # --- Pasos de tubo en EMPALME-01 (tubos 3-12 pasan sin abrir) ---
        for tubo in range(3, 13):
            PasoTubo.objects.create(elemento=empalmes[0], cable=troncal, tubo=tubo)

        # --- Puertos y ~150 fusiones (85% OK / 12% WARNING / 3% FUERA) ---
        bandeja_contador = {}  # elemento -> próxima (bandeja, posicion) libre

        def siguiente_bandeja(elemento):
            n = bandeja_contador.get(elemento.pk, 0)
            bandeja_contador[elemento.pk] = n + 1
            return n // 12 + 1, n % 12 + 1

        def fusionar(elemento, pa, pb):
            bandeja, posicion = siguiente_bandeja(elemento)
            fusion = Fusion(
                elemento=elemento, puerto_a=pa, puerto_b=pb,
                bandeja=bandeja, posicion=posicion,
                estado=random.choice(
                    [Fusion.Estado.MEDIDA, Fusion.Estado.VALIDADA]
                ),
                creada_por=usuarios["fusionador"],
            )
            fusion.full_clean()
            fusion.save()
            return fusion

        def puerto_fibra(elemento, cable, tubo, fibra):
            p = Puerto(
                elemento=elemento, tipo=Puerto.Tipo.FIBRA_CABLE,
                cable=cable, tubo=tubo, fibra=fibra,
            )
            p.full_clean()
            p.save()
            return p

        def puerto_pigtail(elemento):
            return Puerto.objects.create(elemento=elemento, tipo=Puerto.Tipo.PIGTAIL)

        fusiones = []

        # 1) ODF-01: 66 fibras del troncal (tubos 1-6) fusionadas a pigtails.
        fibras_odf = [(t, f) for t in range(1, 7) for f in range(1, 13)][:66]
        for tubo, fibra in fibras_odf:
            fusiones.append(fusionar(
                odf, puerto_fibra(odf, troncal, tubo, fibra), puerto_pigtail(odf)
            ))

        # 2) EMPALME-01: troncal (tubos 1-2) <-> DIST-01 (24 fusiones).
        for tubo in range(1, 3):
            for fibra in range(1, 13):
                fusiones.append(fusionar(
                    empalmes[0],
                    puerto_fibra(empalmes[0], troncal, tubo, fibra),
                    puerto_fibra(empalmes[0], dist_01, tubo, fibra),
                ))

        # 3) EMPALME-02: DIST-01 -> DIST-02 (12) + DIST-05/06 (12 alternas).
        for fibra in range(1, 13):
            fusiones.append(fusionar(
                empalmes[1],
                puerto_fibra(empalmes[1], dist_01, 1, fibra),
                puerto_fibra(empalmes[1], dist_02, 1, fibra),
            ))
        for i, fibra in enumerate(range(1, 13)):
            fusiones.append(fusionar(
                empalmes[1],
                puerto_fibra(empalmes[1], dist_01, 2, fibra),
                puerto_fibra(empalmes[1], dist_cto[2 + (i % 2)], 1, fibra),
            ))

        # 4) EMPALME-03: DIST-02 -> DIST-03 (6) + DIST-04 (6).
        for i, fibra in enumerate(range(1, 13)):
            fusiones.append(fusionar(
                empalmes[2],
                puerto_fibra(empalmes[2], dist_02, 1, fibra),
                puerto_fibra(empalmes[2], dist_cto[i % 2], 1, fibra),
            ))

        # 5) CTOs: fibra de distribución <-> pigtail del splitter (6 por CTO).
        for i, cto in enumerate(ctos):
            for fibra in range(1, 7):
                fusiones.append(fusionar(
                    cto,
                    puerto_fibra(cto, dist_cto[i], 1, fibra),
                    puerto_pigtail(cto),
                ))

        assert len(fusiones) == 150, f"Se esperaban 150 fusiones, hay {len(fusiones)}"

        # Pérdidas: 128 OK / 18 WARNING / 4 FUERA (según umbrales SM 0.05/0.10).
        perdidas = (
            [round(random.uniform(0.010, 0.049), 3) for _ in range(128)]
            + [round(random.uniform(0.050, 0.099), 3) for _ in range(18)]
            + [round(random.uniform(0.100, 0.250), 3) for _ in range(4)]
        )
        random.shuffle(perdidas)
        for fusion, perdida in zip(fusiones, perdidas):
            fusion.perdida_db = Decimal(str(perdida))
            fusion.full_clean()
            fusion.save()

        # 2 fusiones subsanadas: la antigua queda inactiva y apunta a la nueva.
        for vieja in fusiones[:2]:
            nueva = Fusion(
                elemento=vieja.elemento,
                puerto_a=vieja.puerto_a, puerto_b=vieja.puerto_b,
                perdida_db=Decimal("0.020"),
                bandeja=vieja.bandeja, posicion=None,
                estado=Fusion.Estado.VALIDADA,
                creada_por=usuarios["fusionador"],
            )
            # Desactivar primero para liberar los índices únicos parciales.
            vieja.activa = False
            vieja.full_clean()
            vieja.save()
            nueva.full_clean()
            nueva.save()
            vieja.sustituida_por = nueva
            vieja.save()

        # --- Órdenes de trabajo demo ---
        OrdenTrabajo.objects.create(
            obra=obra, tipo=OrdenTrabajo.Tipo.FUSION, trabajador=fusionador,
            fecha=date(2026, 2, 10), estado=OrdenTrabajo.Estado.EN_CURSO,
        )
        OrdenTrabajo.objects.create(
            obra=obra, tipo=OrdenTrabajo.Tipo.MONTAJE_CTO, trabajador=capataz,
            fecha=date(2026, 2, 12), estado=OrdenTrabajo.Estado.ASIGNADA,
        )

        self.stdout.write(self.style.SUCCESS(
            "Seed demo creado: contrata FibraSur, 3 usuarios "
            f"(password '{PASSWORD_DEMO}'), obra OB-2026-014 con "
            f"{len(fusiones) + 2} fusiones."
        ))
