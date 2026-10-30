# Cómo contribuir a sigat-durazno-api

## Ramas

| Rama | Uso | Quién sube |
|---|---|---|
| `develop` | Trabajo diario del equipo | Los desarrolladores con permiso en el repositorio |
| `main` | Versión estable y aprobada | Solo el responsable del repositorio, desde `develop` |

Para una tarea grande puede crear `feature/<nombre>` **desde `develop`** y abrir un Pull Request hacia `develop`.

## Antes de subir, baje siempre primero

```bash
git switch develop
git pull origin develop          # 1. al empezar
# … trabajo y commits …
git pull origin develop          # 2. justo antes de subir: trae lo que subieron los demás
# si hay conflictos: resuélvalos, vuelva a probar y haga commit
make calidad && pytest -m integracion
git push origin develop          # 3. ahora sí
```

- Si `git push` es rechazado, **no fuerce**: vuelva a hacer `git pull origin develop`, resuelva y pruebe.
- Nunca use `git push --force` sobre `develop` ni `main`.

## Buenas prácticas de código (facilitan la revisión)

- Nombres claros, en el idioma que ya usa cada capa del proyecto.
- Funciones cortas, una responsabilidad por función.
- Respetar la estructura existente (cada cosa en su capa y carpeta).
- Sin código comentado, sin mensajes de depuración, sin valores escritos a mano (URLs, claves, IDs).
- Manejar los errores con mensajes útiles; nunca ocultarlos.
- Comentarios que expliquen el **porqué** y las reglas de negocio.
- Tipos explícitos.
- Toda corrección o funcionalidad llega con su prueba.
- Formato automático: `ruff format src tests scripts`.

## Herramientas de calidad

| Qué | Comando |
|---|---|
| Análisis estático | `ruff check src tests scripts` · `mypy` · `lint-imports` |
| Pruebas | `pytest -m "not integracion"` y `pytest -m integracion` |
| Todo junto (lo mismo que la CI) | `make calidad && pytest -m integracion` |

## Pull Requests

- Pequeños y de una sola tarea; título que diga qué hace.
- Descripción con: qué cambia, por qué, cómo se probó y evidencia (capturas o respuestas de la API).
- Revise su propio diff antes de pedir revisión.
- Responda cada comentario y aplique los cambios en la misma rama.

## Nunca suba

`.env`, claves `SIGAT_JWT_SECRETO`, `SIGAT_DB_*`, `SIGAT_S3_*`, `SIGAT_SMTP_*`, `SIGAT_OIDC_*`, volcados de BD, fotos de evidencia, contraseñas, tokens, claves privadas, datos personales o reales. Si sube un secreto por error, avise de inmediato: borrar el archivo no basta, el secreto debe cambiarse.
