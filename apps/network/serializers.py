"""Serializers de la API de network.

Todos los serializers ejecutan ``full_clean()`` del modelo antes de
guardar, de modo que los invariantes I2-I4 también se aplican vía API.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

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


class LimpiadorMixin:
    """Ejecuta la validación de modelo (clean) al crear/actualizar vía API."""

    def _guardar_limpio(self, instancia):
        try:
            instancia.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict or exc.messages)
        instancia.save()
        return instancia

    def create(self, validated_data):
        return self._guardar_limpio(self.Meta.model(**validated_data))

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        return self._guardar_limpio(instance)


class ObraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Obra
        fields = [
            "id", "cliente", "perfil_operadora", "codigo", "direccion",
            "ubicacion", "arquitectura", "estado", "umbrales",
            "potencia_min_dbm", "potencia_max_dbm", "requiere_otdr",
            "creado", "modificado",
        ]
        read_only_fields = ["creado", "modificado"]


class ElementoRedSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElementoRed
        fields = [
            "id", "obra", "tipo", "codigo", "direccion", "ubicacion_tipo",
            "lat", "long", "capacidad_puertos",
        ]


class CableSerializer(serializers.ModelSerializer):
    n_fibras = serializers.ReadOnlyField()

    class Meta:
        model = Cable
        fields = [
            "id", "obra", "elemento_a", "elemento_b", "codigo", "tipo_cable",
            "tipo_fibra", "n_tubos", "fibras_por_tubo", "n_fibras", "longitud_m",
        ]


class PasoTuboSerializer(LimpiadorMixin, serializers.ModelSerializer):
    class Meta:
        model = PasoTubo
        fields = ["id", "elemento", "cable", "tubo"]


class SplitterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Splitter
        fields = ["id", "elemento", "ratio", "cascada_de"]


class PuertoSerializer(LimpiadorMixin, serializers.ModelSerializer):
    class Meta:
        model = Puerto
        fields = [
            "id", "elemento", "tipo", "cable", "tubo", "fibra",
            "splitter", "puerto", "reservado_para",
        ]


class FusionSerializer(LimpiadorMixin, serializers.ModelSerializer):
    nivel = serializers.ReadOnlyField()

    class Meta:
        model = Fusion
        fields = [
            "id", "elemento", "puerto_a", "puerto_b", "perdida_db", "bandeja",
            "posicion", "estado", "activa", "sustituida_por", "version",
            "creada_por", "nivel", "creado", "modificado",
        ]
        read_only_fields = ["version", "creada_por", "creado", "modificado"]


class ConexionSerializer(LimpiadorMixin, serializers.ModelSerializer):
    class Meta:
        model = Conexion
        fields = [
            "id", "elemento", "puerto_a", "puerto_b", "estado", "activa",
            "sustituida_por", "version", "creada_por", "creado", "modificado",
        ]
        read_only_fields = ["version", "creada_por", "creado", "modificado"]


class OrdenTrabajoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdenTrabajo
        fields = ["id", "obra", "tipo", "trabajador", "fecha", "estado"]


class MatrizFilaSerializer(serializers.Serializer):
    """Fila sparse de la matriz de fusiones entre dos cables."""

    fusion_id = serializers.IntegerField()
    tubo_a = serializers.IntegerField(allow_null=True)
    fibra_a = serializers.IntegerField(allow_null=True)
    tubo_b = serializers.IntegerField(allow_null=True)
    fibra_b = serializers.IntegerField(allow_null=True)
    perdida_db = serializers.DecimalField(
        max_digits=5, decimal_places=3, allow_null=True
    )
    nivel = serializers.CharField(allow_null=True)
    estado = serializers.CharField()


class ResumenSerializer(serializers.Serializer):
    """Conteos de fusiones de un elemento por estado y por nivel."""

    elemento = serializers.IntegerField()
    fusiones_activas = serializers.IntegerField()
    por_estado = serializers.DictField(child=serializers.IntegerField())
    por_nivel = serializers.DictField(child=serializers.IntegerField())
    conexiones_activas = serializers.IntegerField()
