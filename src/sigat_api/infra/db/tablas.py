"""Definiciones SQLAlchemy Core del esquema ``sigat``.

DECISIÓN: el backend NO es dueño del esquema SIGAT. Lo instala y versiona el
paquete de BD (v8). Aquí solo se DESCRIBEN las tablas para consultarlas.

Cómo se llena este módulo (una vez, y cada vez que cambie la BD):

    make tablas      # sqlacodegen --generator tables --schemas sigat -> tablas_generadas.py

y se reexportan desde aquí las que use cada repositorio. Reglas:

* Las tablas de registros de campo son APPEND-ONLY (ADR-03): lectura_trampa,
  aplicacion_fitosanitaria, cosecha, etapa_declarada, hallazgo,
  bpa_verificacion, manejo_agronomico, estimacion_produccion, indice_mtd,
  concepto_aptitud, bitacora_auditoria, operacion_sync, recepcion_sync.
  Ningún repositorio emite UPDATE/DELETE sobre ellas: la BD lo bloquea.
* ``visita`` solo admite UPDATE de las columnas de revisión.
* Las lecturas de pantalla salen preferentemente de las VISTAS (``v_*_app``,
  ``v_*_vigente``) y de las funciones ``fn_*_app(usua)`` que ya filtran por
  ``fn_lotes_visibles``.
"""

from sqlalchemy import MetaData

metadata = MetaData(schema="sigat")

# from sigat_api.infra.db.tablas_generadas import lote, predio, trampa, ...
