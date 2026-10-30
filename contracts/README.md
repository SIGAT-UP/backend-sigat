# Contrato OpenAPI

`openapi.json` es el **único artefacto** que cruza del backend a los fronts (Arquitectura §9.1, ADR-16).
Se genera desde el código con `make contrato` y la CI falla si no coincide (`make contrato-verificar`).

Cómo lo consumen los fronts:
* **Móvil (Flutter)**: fija una copia versionada en `lib/contracts/openapi.json` y genera el cliente
  (`openapi-generator-cli generate -g dart-dio`). No editar el cliente generado.
* **Web (React)**: `npx openapi-typescript contracts/openapi.json -o src/data/http/api.d.ts`
  y escribe los repositorios de `src/data/http/` sobre esos tipos.

Un cambio incompatible (quitar campo, cambiar tipo, endurecer validación) rompe la app ya instalada en
campo: se versiona (`/api/v2`) o se hace aditivo.
