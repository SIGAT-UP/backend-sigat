"""Módulo CATÁLOGO.

Responsabilidad: valores de referencia que usan formularios y reglas
(condición de trampa, atrayente, producto fitosanitario, plaga, severidad,
fenología, unidades, especie de mosca, etc.) y la geografía DANE.

Frontera de datos: arbol, atrayente, centro_acopio, condicion_trampa,
departamento, municipio, region, rango_departamento, escenario_trampeo,
especie_cultivo, variedad_cultivo, especie_mosca, estado_registro, fenologia,
fenologia_regla, localizacion, norma, producto_fitosanitario, tipo_trampa,
unidad_medida, vigilancia, plaga_enfermedad, severidad, criterio_bpa,
tipo_manejo.

Regla: un valor de catálogo usado por un registro NUNCA se borra; se retira
(``*_activo = false``) para conservar la historia. Los catálogos sin valores
oficiales los carga la institución (docs/09_pendientes_institucionales de la BD).
"""
