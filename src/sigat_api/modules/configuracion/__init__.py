"""Módulo CONFIGURACIÓN DE PREDIOS (contenedor 5 del C4).

Responsabilidad: predios, lotes y su geometría versionada (ADR-06), trampas y
su ubicación/asignación al lote (RN-013), programa de inspección versionado con
vigencia (ADR-05, ADR-07), retícula (RN-004) y PAQUETE DE CAMPO (ADR-09) que el
móvil descarga para trabajar sin red.

Frontera de datos: predio, lote, lote_geometria, reticula, reticula_celda,
programa_inspeccion, programa_umbral, programa_criterio_bpa, paquete_campo,
trampa, ubicacion_trampa, ruta.

Regla ADR-07: NO hay ``if predio == ...`` en el código. Todo lo que cambia entre
predios es un dato de ``programa_inspeccion``.
"""
