# Cambios de la base de datos

Este documento establece las convenciones para administrar y mantener la estructura de la base de datos de SIGAT.

Su objetivo es mantener la trazabilidad de los cambios, facilitar el mantenimiento y garantizar que las modificaciones sean consistentes entre los diferentes entornos del sistema.

## Gestión de la estructura

La estructura de la base de datos se administra mediante scripts SQL y migraciones de Alembic.

Este mecanismo permite:

- Crear la estructura de la base de datos.
- Incorporar nuevas tablas, relaciones y restricciones.
- Actualizar índices, vistas y funciones.
- Mantener los catálogos y datos de referencia.
- Aplicar modificaciones de forma controlada.
- Conservar la consistencia entre los entornos de ejecución.

Las migraciones deben ejecutarse siguiendo el orden establecido por el proyecto.

Para aplicar las migraciones:

```bash
alembic upgrade head
```

Para consultar el historial:

```bash
alembic history
```

Para consultar la revisión actual:

```bash
alembic current
```

## Organización de los cambios

Los cambios de estructura se gestionan mediante dos mecanismos:

| Mecanismo | Responsabilidad |
|---|---|
| Scripts SQL | Definición y mantenimiento de los elementos de la base de datos |
| Alembic | Control de versiones y ejecución ordenada de migraciones |

Los archivos SQL se organizan en el directorio `bd/sql/`, mientras que las migraciones se almacenan en `migrations/`.

Cada modificación debe estar documentada y asociada con su correspondiente cambio en el proyecto.

## Principios para modificar la base de datos

Las modificaciones deben seguir estas buenas prácticas:

1. **Conservar el historial:** no modificar migraciones que ya hayan sido aplicadas en otros entornos. Los cambios nuevos deben incorporarse mediante nuevas revisiones.
2. **Priorizar cambios compatibles:** procurar que las modificaciones no afecten innecesariamente la información existente.
3. **Mantener la integridad:** conservar las relaciones, restricciones y reglas de validación de los datos.
4. **Documentar los cambios:** describir el propósito y el alcance de cada modificación.
5. **Verificar las migraciones:** comprobar que los cambios puedan aplicarse correctamente.
6. **Evitar pérdidas de información:** evaluar cuidadosamente cualquier modificación que pueda alterar o eliminar datos existentes.

## Procedimiento para incorporar cambios

Cuando sea necesario modificar la estructura de la base de datos, se recomienda seguir este procedimiento:

### 1. Identificar la modificación

Determinar qué elemento necesita cambiarse y cuál es el propósito de la modificación.

### 2. Crear una nueva migración

Generar una revisión mediante Alembic:

```bash
alembic revision -m "descripcion_del_cambio"
```

### 3. Implementar el cambio

Incorporar las operaciones necesarias en la migración, procurando mantener la compatibilidad con la estructura existente.

### 4. Documentar la modificación

Registrar qué cambia, cuál es su propósito y qué consideraciones deben tenerse en cuenta al aplicarlo.

### 5. Ejecutar las verificaciones

Aplicar las migraciones:

```bash
alembic upgrade head
```

Ejecutar las pruebas de integración:

```bash
pytest -m integracion
```

### 6. Revisar y compartir

Comprobar los resultados, revisar los cambios y seguir el flujo de contribución establecido en el repositorio.

## Integridad y protección de los datos

La administración de la base de datos debe considerar las siguientes medidas:

- Mantener las relaciones y restricciones de integridad referencial.
- Evitar modificaciones que comprometan información existente.
- Evaluar los cambios antes de aplicarlos en entornos compartidos.
- Realizar respaldos cuando las operaciones puedan afectar información almacenada.
- No incorporar credenciales, contraseñas, tokens ni información sensible en los scripts SQL.
- No almacenar volcados de bases de datos ni información personal real dentro del repositorio.

## Convenciones de desarrollo

Para mantener una estructura organizada y consistente:

- Utilizar nombres descriptivos para las migraciones.
- Mantener un orden lógico de ejecución.
- Evitar duplicar definiciones existentes.
- Documentar las modificaciones relevantes.
- Mantener sincronizados los scripts SQL y las migraciones correspondientes.
- Verificar los cambios antes de integrarlos a la rama principal.

---

**SIGAT — Sistema de Información para la Gestión y Análisis de la Vigilancia Fitosanitaria.**