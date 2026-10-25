#!/bin/sh
# Entrypoint de ica-durazno-api.
#
# Ejecuta las migraciones solo si RUN_MIGRATIONS=1. Por defecto no las ejecuta:
# en Coolify conviene correr `alembic upgrade head` una vez por release desde la
# terminal, para que un reinicio o un despliegue con varias instancias no compita
# por la misma migración.
set -eu

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "==> alembic upgrade head"
  alembic upgrade head
fi

exec "$@"
