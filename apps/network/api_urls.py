"""Rutas de la API REST de FiberDoc (DRF DefaultRouter)."""
from rest_framework.routers import DefaultRouter

from .views import (
    CableViewSet,
    ConexionViewSet,
    ElementoRedViewSet,
    FusionViewSet,
    ObraViewSet,
    OrdenTrabajoViewSet,
    PasoTuboViewSet,
    PuertoViewSet,
    SplitterViewSet,
)

router = DefaultRouter()
router.register("obras", ObraViewSet, basename="obras")
router.register("elementos", ElementoRedViewSet, basename="elementos")
router.register("cables", CableViewSet, basename="cables")
router.register("fusiones", FusionViewSet, basename="fusiones")
router.register("conexiones", ConexionViewSet, basename="conexiones")
router.register("pasos-tubo", PasoTuboViewSet, basename="pasos-tubo")
router.register("splitters", SplitterViewSet, basename="splitters")
router.register("puertos", PuertoViewSet, basename="puertos")
router.register("ordenes", OrdenTrabajoViewSet, basename="ordenes")

urlpatterns = router.urls
