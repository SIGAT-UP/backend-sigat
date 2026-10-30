"""Módulo SINCRONIZACIÓN (contenedor 3 del C4).

Componentes (Arquitectura §6.3):
* Receptor de lotes      -> ``servicio.ServicioSincronizacion.recibir`` (responde rápido; NO reprocesa).
* Clasificador           -> idempotencia/conflicto aquí (``huella.py``, recepcion_sync) y la
                            clasificación temporal se delega al núcleo de Registro (puerto).
* Encolador de reproceso -> encola ``reprocesar_periodo`` por cada periodo afectado.
* Procesador de reproceso-> ``procesador.py`` (lo ejecuta el worker): recalcula MTD (Registro)
                            y reemite el concepto (Concepto) con su fecha de efecto.

Frontera de datos: dispositivo, operacion_sync, recepcion_sync (+ planificacion_lote.plal_oper_id
lo escribe Planificación a través del puerto).
"""
