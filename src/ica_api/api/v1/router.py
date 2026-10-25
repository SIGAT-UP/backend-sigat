"""Router raíz de la API versionada.

Cada módulo expone su propio router; aquí solo se componen. Un módulo nuevo se
agrega con una línea y no toca los demás.
"""

from fastapi import APIRouter

from ica_api import __version__
from ica_api.modules.administracion.api.router import router as administracion_router
from ica_api.modules.calidad.api.router import router as calidad_router
from ica_api.modules.concepto.api.router import router as concepto_router
from ica_api.modules.configuracion.api.router import router as configuracion_router
from ica_api.modules.identidad.api.router import router as identidad_router
from ica_api.modules.imagenes.api.router import router as imagenes_router
from ica_api.modules.importacion.api.router import router as importacion_router
from ica_api.modules.laboratorio.api.router import router as laboratorio_router
from ica_api.modules.registro.api.router import router as registro_router
from ica_api.modules.reportes.api.router import router as reportes_router
from ica_api.modules.sincronizacion.api.router import router as sincronizacion_router

api_router = APIRouter()


@api_router.get("/version", tags=["sistema"])
def version() -> dict[str, str]:
    return {"version": __version__}


for router in (
    identidad_router,
    sincronizacion_router,
    registro_router,
    configuracion_router,
    imagenes_router,
    concepto_router,
    reportes_router,
    administracion_router,
    importacion_router,
    laboratorio_router,
    calidad_router,
):
    api_router.include_router(router)
