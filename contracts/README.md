# Contratos

Aquí se publica el `openapi.json` generado por la API. Es el único artefacto
que cruza a los repositorios de la web y del móvil.

```bash
uv run python -m scripts.export_openapi
```

El archivo se versiona con la etiqueta del release (`openapi-0.1.0.json`) y los
clientes lo fijan; no se edita a mano.
