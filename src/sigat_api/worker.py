"""Proceso de la cola de trabajo: ``python -m sigat_api.worker``.

Mismo código e imagen que la API (ADR-14). Registra las tareas de ``infra/cola``
y compone sus dependencias igual que ``api/fabricas.py``, pero con una
transacción por tarea y un actor de sistema para ``sigat.usuario_actual``
(pendiente institucional: qué usua_id representa al "sistema" en la bitácora).
"""

import asyncio

from sigat_api.config import obtener_configuracion
from sigat_api.infra.db.motor import cerrar_motor, crear_motor
from sigat_api.infra.observabilidad.logs import configurar_logs


async def principal() -> None:
    cfg = obtener_configuracion()
    configurar_logs(cfg)
    crear_motor(cfg)
    try:
        # Pendiente: app procrastinate -> app.run_worker_async(concurrency=cfg.cola_concurrencia)
        # Tareas: reprocesar_periodo -> sincronizacion.procesador.ProcesadorReproceso
        #         generar_paquete_campo -> configuracion.servicio.ServicioPaqueteCampo.generar
        #         verificar_archivo -> imagenes.servicio.ServicioArchivos
        #         enviar_correo -> infra.correo.enviar
        raise NotImplementedError("Worker de la cola pendiente de implementar")
    finally:
        await cerrar_motor()


if __name__ == "__main__":
    asyncio.run(principal())
