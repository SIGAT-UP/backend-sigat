# Migraciones del backend

El backend de SIGAT utiliza un sistema de migraciones para administrar los componentes de base de datos que pertenecen a su propia infraestructura.

La gestión de la estructura se encuentra separada por responsabilidades, lo que permite mantener la independencia entre la base de datos institucional y los componentes técnicos utilizados por el backend.

## 1. Organización de los esquemas

La base de datos contempla diferentes esquemas, cada uno con una responsabilidad específica:

| Esquema | Responsabilidad |
|---|---|
| `sigat` | Contiene la estructura institucional y los elementos propios del modelo de datos de SIGAT. |
| `api` | Agrupa los componentes técnicos utilizados por el backend para gestionar sesiones y procesos de autenticación. |
| `cola` | Contiene los elementos necesarios para la gestión de tareas y procesos en segundo plano. |

El backend administra sus propios componentes mediante sus herramientas de migración. La estructura institucional se mantiene bajo la responsabilidad de su mecanismo de administración correspondiente.

Esta separación evita duplicar responsabilidades y facilita el mantenimiento de los diferentes componentes del sistema.

## 2. Herramientas de administración

El proyecto utiliza las siguientes herramientas para gestionar la estructura de datos:

- **Alembic:** administra las versiones y la ejecución ordenada de las migraciones del backend.
- **PostgreSQL:** proporciona el sistema de gestión de bases de datos.
- **Procrastinate:** permite gestionar la infraestructura de tareas en segundo plano y sus componentes asociados.

Cada herramienta cumple una función específica dentro de la arquitectura.

## 3. Preparación de un entorno nuevo

La preparación de un entorno requiere que los componentes de base de datos estén disponibles antes de iniciar los servicios que dependen de ellos.

El procedimiento general contempla las siguientes etapas:

### Etapa 1. Preparación de la base de datos institucional

Instalar previamente la estructura institucional de SIGAT mediante el mecanismo de instalación definido para el paquete de base de datos.

Esta etapa proporciona las tablas, relaciones y demás elementos requeridos por el sistema.

### Etapa 2. Aplicación de las migraciones del backend

Una vez disponible la estructura institucional, ejecutar las migraciones correspondientes al backend:

```bash
alembic upgrade head
```

Alembic aplica las revisiones disponibles y actualiza los componentes propios del backend.

### Etapa 3. Preparación de la infraestructura de tareas

Configurar los elementos necesarios para la gestión de tareas en segundo plano mediante la herramienta correspondiente.

Esta etapa permite disponer de la infraestructura requerida para los procesos asíncronos del sistema.

## 4. Administración de migraciones

Para mantener un control organizado de las modificaciones, se deben seguir estas convenciones:

- Cada cambio nuevo debe incorporarse mediante una migración independiente.
- Las migraciones deben conservar un orden de ejecución coherente.
- No se deben modificar revisiones que ya hayan sido aplicadas en otros entornos.
- Los cambios deben mantener la compatibilidad con los componentes existentes.
- Las modificaciones deben verificarse antes de integrarse al proyecto.

Para consultar el historial de migraciones:

```bash
alembic history
```

Para consultar la revisión aplicada en el entorno actual:

```bash
alembic current
```

## 5. Consideraciones importantes

- La estructura institucional y los componentes propios del backend tienen mecanismos de administración independientes.
- Las migraciones del backend no deben utilizarse para reemplazar ni reconstruir la estructura institucional.
- La infraestructura de tareas en segundo plano debe prepararse de acuerdo con los requisitos del servicio correspondiente.
- Antes de aplicar modificaciones en entornos compartidos, se deben verificar sus efectos sobre la integridad de los datos.
- Las operaciones que puedan afectar información existente deben evaluarse cuidadosamente y contar con respaldos cuando corresponda.

## 6. Mantenimiento y consistencia

La correcta administración de las migraciones permite mantener una estructura organizada, facilitar la configuración de nuevos entornos y reducir inconsistencias entre instalaciones.

Los cambios relacionados con la base de datos deben coordinarse con las responsabilidades de cada componente de SIGAT, conservando la separación entre la infraestructura institucional y la infraestructura del backend.

---

**SIGAT — Sistema de Información para la Gestión y Análisis de la Vigilancia Fitosanitaria.**