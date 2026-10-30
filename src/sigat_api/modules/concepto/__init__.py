"""Módulo CONCEPTO Y REPORTES (contenedor 7 del C4; candidato a extracción, ADR-14).

Responsabilidad: emitir y reemitir el CONCEPTO DE APTITUD por lote y periodo con
su fecha de efecto (Arquitectura §4.4), reconstruir el estado de un lote "a una
fecha" (RF-024) y servir los modelos de lectura de resumen: resumen fitosanitario
del lote, serie del MTD, estado del cultivo del productor.

Frontera de datos: concepto_aptitud. Lee las VISTAS publicadas por la BD
(v_mtd_serie_lote, v_mtd_vigente, v_concepto_vigente, v_lote_resumen_app,
v_resumen_lote, v_etapa_discrepancia, v_estimacion_total) y fn_etapa_derivada.
Decisión: leer vistas (solo lectura) es su contrato con el núcleo; si el módulo
se extrae como servicio, esas vistas pasan a una réplica de lectura.

ADR-15: toda cifra de aquí es la AUTORIZADA; el móvil marca la suya como estimación.
"""
