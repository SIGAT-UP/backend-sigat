"""Módulo NÚCLEO DE REGISTRO E HISTORIAL (contenedor 4 del C4).

Responsabilidad: almacenar las mediciones de campo de forma APPEND-ONLY con
versiones (ADR-03), resolver el orden temporal (motor temporal, ``dominio.py``),
validar invariantes (``validador.py``), la revisión del agrónomo sobre la visita
y las consultas de historial. Es el ÚNICO lugar donde se decide cómo se ordena
el pasado (Arquitectura §9.2, regla 3).

Incluye el MOTOR DE UMBRALES MTD (Arquitectura §6.3, ``mtd.py``): agrega el
muestreo del periodo y lo contrasta con el umbral vigente A LA FECHA DEL PERIODO.

Frontera de datos: visita, visita_lote, lectura_trampa, aplicacion_fitosanitaria,
cosecha, etapa_declarada, hallazgo, bpa_verificacion, manejo_agronomico,
estimacion_produccion, periodo_trampeo, indice_mtd, indice_mtd_lectura. Lee: v_lectura_vigente, v_actividad_lote, v_registro_campo,
v_visita_lote_sin_asignacion, v_etapa_discrepancia, v_mtd_vigente,
fn_mtd_lectura_valida(peri).

Toda escritura de un registro versionado —venga del móvil por sincronización
o de la web en línea— entra por ``ServicioRegistro.aplicar`` y queda ligada a
una fila de ``operacion_sync`` (la BD exige ``oper_id`` y ``disp_id``).
"""
