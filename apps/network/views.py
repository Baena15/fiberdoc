"""ViewSets de la API de network.

Todos los querysets se filtran por ``request.user.contrata`` (aislamiento
multi-tenant): un usuario de la contrata B obtiene 404 al pedir un objeto
de la contrata A porque ni siquiera está en el queryset.
"""
from collections import Counter

from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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
from .permissions import IsSameContrata
from .serializers import (
    CableSerializer,
    ConexionSerializer,
    ElementoRedSerializer,
    FusionSerializer,
    MatrizFilaSerializer,
    ObraSerializer,
    OrdenTrabajoSerializer,
    PasoTuboSerializer,
    PuertoSerializer,
    ResumenSerializer,
    SplitterSerializer,
)


class TenantViewSet(viewsets.ModelViewSet):
    """Base: filtra por la contrata del usuario autenticado."""

    permission_classes = [IsSameContrata]

    def contrata_usuario(self):
        return self.request.user.contrata


class ObraViewSet(TenantViewSet):
    serializer_class = ObraSerializer

    def get_queryset(self):
        return Obra.objects.filter(contrata=self.contrata_usuario()).select_related(
            "cliente", "perfil_operadora"
        )

    def perform_create(self, serializer):
        serializer.save(contrata=self.request.user.contrata)


class ElementoRedViewSet(TenantViewSet):
    serializer_class = ElementoRedSerializer

    def get_queryset(self):
        return ElementoRed.objects.filter(
            obra__contrata=self.contrata_usuario()
        ).select_related("obra")

    @extend_schema(responses=ResumenSerializer)
    @action(detail=True, methods=["get"])
    def resumen(self, request, pk=None):
        """Conteos de fusiones activas del elemento por estado y por nivel.

        Se hace con dos consultas (una agregada por estado y una de valores
        para clasificar por nivel con los umbrales de la obra); no hay N+1.
        """
        elemento = self.get_object()
        por_estado = dict(
            Fusion.objects.filter(elemento=elemento, activa=True)
            .values_list("estado")
            .annotate(total=Count("id"))
        )
        # Valores mínimos para calcular el nivel en memoria con los umbrales.
        fusiones = (
            Fusion.objects.filter(elemento=elemento, activa=True)
            .select_related("puerto_a__cable", "elemento__obra")
        )
        por_nivel = Counter()
        for fusion in fusiones:
            por_nivel[fusion.nivel or "SIN_MEDIDA"] += 1
        datos = {
            "elemento": elemento.id,
            "fusiones_activas": sum(por_estado.values()),
            "por_estado": por_estado,
            "por_nivel": dict(por_nivel),
            "conexiones_activas": Conexion.objects.filter(
                elemento=elemento, activa=True
            ).count(),
        }
        return Response(ResumenSerializer(datos).data)

    @extend_schema(
        parameters=[
            OpenApiParameter("cable_a", int, required=True),
            OpenApiParameter("cable_b", int, required=True),
        ],
        responses=MatrizFilaSerializer(many=True),
    )
    @action(detail=True, methods=["get"])
    def matriz(self, request, pk=None):
        """Filas sparse de fusiones activas entre dos cables del elemento.

        Devuelve solo las fusiones existentes (formato sparse) con la
        posición de cada fibra en ambos cables, pensado para la futura
        matriz React. ``cable_a``/``cable_b`` son ids; el orden es
        indiferente (se consideran ambas orientaciones).
        """
        elemento = self.get_object()
        cable_a = request.query_params.get("cable_a")
        cable_b = request.query_params.get("cable_b")
        if not cable_a or not cable_b:
            return Response(
                {"detail": "Faltan los parámetros cable_a y/o cable_b."}, status=400
            )
        fusiones = (
            Fusion.objects.filter(elemento=elemento, activa=True)
            .filter(
                Q(puerto_a__cable_id=cable_a, puerto_b__cable_id=cable_b)
                | Q(puerto_a__cable_id=cable_b, puerto_b__cable_id=cable_a)
            )
            .select_related("puerto_a__cable", "puerto_b__cable", "elemento__obra")
            .order_by("id")
        )
        filas = []
        for fusion in fusiones:
            # Normalizar la orientación: el puerto del cable_a siempre como "a".
            pa, pb = fusion.puerto_a, fusion.puerto_b
            if str(pa.cable_id) != str(cable_a):
                pa, pb = pb, pa
            filas.append(
                {
                    "fusion_id": fusion.id,
                    "tubo_a": pa.tubo,
                    "fibra_a": pa.fibra,
                    "tubo_b": pb.tubo,
                    "fibra_b": pb.fibra,
                    "perdida_db": fusion.perdida_db,
                    "nivel": fusion.nivel,
                    "estado": fusion.estado,
                }
            )
        return Response(
            {
                "elemento": elemento.id,
                "cable_a": int(cable_a),
                "cable_b": int(cable_b),
                "filas": MatrizFilaSerializer(filas, many=True).data,
            }
        )


class CableViewSet(TenantViewSet):
    serializer_class = CableSerializer

    def get_queryset(self):
        return Cable.objects.filter(
            obra__contrata=self.contrata_usuario()
        ).select_related("obra", "elemento_a", "elemento_b")


class PasoTuboViewSet(TenantViewSet):
    serializer_class = PasoTuboSerializer

    def get_queryset(self):
        return PasoTubo.objects.filter(
            elemento__obra__contrata=self.contrata_usuario()
        ).select_related("elemento", "cable")


class SplitterViewSet(TenantViewSet):
    serializer_class = SplitterSerializer

    def get_queryset(self):
        return Splitter.objects.filter(
            elemento__obra__contrata=self.contrata_usuario()
        ).select_related("elemento", "cascada_de")


class PuertoViewSet(TenantViewSet):
    serializer_class = PuertoSerializer

    def get_queryset(self):
        return Puerto.objects.filter(
            elemento__obra__contrata=self.contrata_usuario()
        ).select_related("elemento", "cable", "splitter")


class FusionViewSet(TenantViewSet):
    serializer_class = FusionSerializer

    def get_queryset(self):
        return Fusion.objects.filter(
            elemento__obra__contrata=self.contrata_usuario()
        ).select_related("elemento", "puerto_a", "puerto_b", "creada_por")

    def perform_create(self, serializer):
        serializer.save(creada_por=self.request.user)


class ConexionViewSet(TenantViewSet):
    serializer_class = ConexionSerializer

    def get_queryset(self):
        return Conexion.objects.filter(
            elemento__obra__contrata=self.contrata_usuario()
        ).select_related("elemento", "puerto_a", "puerto_b", "creada_por")

    def perform_create(self, serializer):
        serializer.save(creada_por=self.request.user)


class OrdenTrabajoViewSet(TenantViewSet):
    serializer_class = OrdenTrabajoSerializer

    def get_queryset(self):
        return OrdenTrabajo.objects.filter(
            obra__contrata=self.contrata_usuario()
        ).select_related("obra", "trabajador")
