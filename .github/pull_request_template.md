## Qué cambia

## Requisitos / ADR que atiende
<!-- RF-xxx, RN-xxx, ADR-xx -->

## Lista de verificación
- [ ] Bajé los cambios de `develop` justo antes de abrir el PR (`git pull origin develop`) y no hay conflictos
- [ ] `make calidad` en verde (formato, lint, tipos, fronteras, pruebas, contrato)
- [ ] Si cambió un endpoint: `make contrato` y el `contracts/openapi.json` va en este PR
- [ ] El cambio de contrato es compatible con la app ya instalada en campo (o se versiona)
- [ ] No hay condicionales por predio en el código (ADR-07)
- [ ] No hay UPDATE sobre tablas append-only (ADR-03)
- [ ] Sin secretos, datos reales ni binarios

## Base de datos (solo si toca `migrations/` o `bd/`)
- [ ] La revisión nueva está descrita en `bd/CAMBIOS.md` (qué hace y por qué)
- [ ] `pytest -m integracion` en verde: instalación limpia y actualización de una base existente
- [ ] No hay volcados, datos reales, contraseñas ni hashes de contraseña
- [ ] ¿Elimina tablas, columnas, restricciones o datos, o modifica filas existentes?
  - [ ] No
  - [ ] Sí: justificación técnica y plan para conservar la información ↓ (requiere la etiqueta
        `bd-destructivo-aprobado`, que pone el responsable de la base de datos)
