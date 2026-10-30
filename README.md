# 🍑 SIGAT — Backend API REST

**Sistema de Información para la Gestión y Análisis de la Vigilancia Fitosanitaria**

Backend de SIGAT, una plataforma orientada a la gestión de información fitosanitaria, vigilancia del cultivo de durazno y seguimiento de la mosca del Mediterráneo (*Ceratitis capitata*).

Este repositorio contiene la API REST que permite la comunicación entre las aplicaciones cliente de SIGAT y los servicios de datos del sistema.

La API proporciona una interfaz centralizada para gestionar solicitudes, validar información y aplicar mecanismos de autenticación y autorización.

## Aplicaciones cliente

El backend está diseñado para integrarse con diferentes aplicaciones del ecosistema SIGAT:

- **SIGAT Web:** aplicación web para la gestión y consulta de información.
- **SIGAT Móvil:** aplicación desarrollada con Flutter para el trabajo de campo y la interacción con los servicios del sistema.

Ambas aplicaciones se comunican con el backend mediante solicitudes HTTP y utilizan formatos de intercambio de información estandarizados.

---

## Tecnologías utilizadas

| Tecnología | Función |
|---|---|
| Python 3.12 | Lenguaje principal |
| FastAPI | Framework para construir la API REST |
| PostgreSQL 16 | Sistema de gestión de bases de datos |
| PostGIS 3.4 | Extensión para información geográfica |
| SQLAlchemy 2 | Acceso a la base de datos |
| asyncpg | Conector asíncrono de PostgreSQL |
| Alembic | Gestión de migraciones |
| Pydantic 2 | Validación y estructuración de datos |
| PyJWT | Gestión de tokens JWT |
| Argon2id | Protección de contraseñas |
| pytest | Pruebas automatizadas |
| Ruff | Análisis y formato del código |
| mypy | Verificación estática de tipos |
| Docker | Contenedorización y entorno de ejecución |

---

## Arquitectura general

El backend utiliza una arquitectura modular organizada por responsabilidades. Esta organización separa la recepción de solicitudes, las reglas de negocio y los servicios de infraestructura.

### Flujo de comunicación

```text
┌──────────────────────┐
│      SIGAT WEB       │
│        React         │
└──────────┬───────────┘
           │
           │ HTTP / JSON
           │
┌──────────▼───────────┐
│      SIGAT API       │
│       FastAPI        │
└──────────┬───────────┘
           │
           ├─────────────────────┐
           │                     │
┌──────────▼───────────┐  ┌──────▼──────────────┐
│     SIGAT MÓVIL      │  │ Servicios internos  │
│       Flutter        │  │                     │
└──────────────────────┘  └──────┬──────────────┘
                                 │
                         ┌───────▼────────┐
                         │  PostgreSQL    │
                         │   + PostGIS    │
                         └────────────────┘
```

### Organización por capas

| Capa | Responsabilidad |
|---|---|
| API | Recibe solicitudes HTTP, valida entradas y construye respuestas. |
| Módulos | Agrupa los servicios y las reglas de negocio. |
| Infraestructura | Gestiona conexiones, seguridad, almacenamiento y servicios externos. |
| Compartido | Contiene elementos comunes, errores y definiciones reutilizables. |
| Configuración | Centraliza las variables y parámetros de ejecución. |

### Comunicación entre módulos

Los módulos se organizan por responsabilidades y utilizan interfaces o puertos para establecer sus dependencias.

La composición de los servicios se centraliza en la capa API, favoreciendo la separación de responsabilidades, el mantenimiento y las pruebas.

---

## Organización funcional

El código fuente se encuentra organizado en módulos que representan diferentes áreas del sistema:

| Módulo | Área de responsabilidad |
|---|---|
| Identidad | Usuarios, autenticación, roles, permisos y sesiones. |
| Catálogo | Catálogos de referencia y datos geográficos. |
| Configuración | Información relacionada con predios, lotes, geometrías y trampas. |
| Registro | Gestión de visitas, lecturas y registros de campo. |
| Sincronización | Comunicación e intercambio de información con dispositivos móviles. |
| Imágenes | Gestión de archivos, fotografías y evidencias. |
| Concepto | Información relacionada con conceptos y resúmenes fitosanitarios. |
| Planificación | Organización de actividades y planificaciones. |
| Notificaciones | Gestión de avisos y notificaciones. |
| Auditoría | Trazabilidad y consulta de registros de operaciones. |

---

## Base de datos

El sistema utiliza PostgreSQL con PostGIS para gestionar información estructurada y datos geográficos.

La organización de los datos contempla una separación de responsabilidades entre la estructura institucional y los componentes técnicos utilizados por el backend.

### Esquemas principales

| Esquema | Responsabilidad |
|---|---|
| `sigat` | Contiene la estructura institucional y la información propia del modelo de datos de SIGAT. |
| `api` | Agrupa componentes técnicos utilizados por el backend, como la gestión de sesiones. |
| `cola` | Aloja los elementos asociados a la gestión de tareas en segundo plano. |

### Gestión de migraciones

Las migraciones de los componentes propios del backend se administran mediante Alembic.

La estructura institucional se administra mediante su mecanismo de instalación y mantenimiento correspondiente.

Para consultar el historial de migraciones:

```bash
alembic history
```

Para conocer la revisión aplicada:

```bash
alembic current
```

Para aplicar las migraciones del backend:

```bash
alembic upgrade head
```

La documentación general de los cambios se encuentra en `bd/CAMBIOS.md`.

---

## Seguridad y autenticación

El backend incorpora mecanismos de seguridad para proteger las operaciones y la información gestionada por el sistema.

### Autenticación

Entre los mecanismos utilizados se encuentran:

- Autenticación basada en tokens JWT.
- Gestión de sesiones y renovación de credenciales.
- Protección de contraseñas mediante Argon2id.
- Validación del estado de las cuentas.
- Gestión de sesiones y mecanismos de revocación.

### Autorización

El sistema contempla diferentes perfiles de acceso según las responsabilidades de los usuarios:

| Rol | Descripción |
|---|---|
| ADMINISTRADOR | Gestión administrativa del sistema. |
| AGRONOMO_SUPERVISOR | Supervisión y consulta de información fitosanitaria. |
| TECNICO | Actividades de campo y registro de información. |
| PRODUCTOR | Consulta y gestión de información relacionada con su actividad productiva. |

Los permisos se validan en el servidor. La identidad y el contexto de autorización se obtienen mediante los mecanismos de autenticación del backend.

### Manejo de errores

Las respuestas de error utilizan el formato `application/problem+json`, siguiendo el estándar RFC 9457.

Este formato permite entregar información estructurada para facilitar la identificación y el manejo de errores por parte de las aplicaciones cliente.

---

## Estructura del proyecto

```text
sigat-durazno-api/
│
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── workflows/
│
├── bd/
│   ├── sql/
│   └── CAMBIOS.md
│
├── contracts/
│   ├── openapi.json
│   └── README.md
│
├── migrations/
│   ├── versions/
│   ├── env.py
│   ├── README.md
│   └── script.py.mako
│
├── scripts/
│
├── src/
│   └── sigat_api/
│       ├── api/
│       │   └── v1/
│       │       └── rutas/
│       │
│       ├── compartido/
│       │
│       ├── infra/
│       │   ├── almacenamiento/
│       │   ├── cola/
│       │   ├── db/
│       │   ├── observabilidad/
│       │   └── seguridad/
│       │
│       └── modules/
│           ├── auditoria/
│           ├── catalogo/
│           ├── concepto/
│           ├── configuracion/
│           ├── identidad/
│           ├── imagenes/
│           ├── notificaciones/
│           ├── planificacion/
│           ├── registro/
│           └── sincronizacion/
│
├── tests/
│   ├── contrato/
│   ├── integracion/
│   ├── modules/
│   └── unit/
│
├── .dockerignore
├── .editorconfig
├── .env.example
├── .gitattributes
├── .gitignore
├── .pre-commit-config.yaml
├── .python-version
├── alembic.ini
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml
├── README.md
├── requirements-dev.txt
├── requirements.txt
└── SECURITY.md
```

### Responsabilidad de los directorios

- `src/sigat_api/api/`: rutas, dependencias, middleware y composición de servicios.
- `src/sigat_api/modules/`: módulos y reglas de negocio.
- `src/sigat_api/infra/`: conexiones y servicios de infraestructura.
- `src/sigat_api/compartido/`: componentes y definiciones comunes.
- `bd/sql/`: scripts SQL de la base de datos institucional.
- `migrations/`: revisiones de Alembic.
- `contracts/`: contrato OpenAPI de la API.
- `tests/`: pruebas unitarias, de módulos, contrato e integración.
- `scripts/`: herramientas auxiliares de mantenimiento y validación.

---

## Requisitos previos

Para preparar un entorno de ejecución se necesitan:

- Python 3.12.
- Git.
- Docker Desktop o PostgreSQL 16 con PostGIS 3.4.
- Acceso a las dependencias del proyecto.
- Configuración de las variables de entorno necesarias.

Comprobar las versiones:

```bash
python --version
git --version
```

---

## Instalación y ejecución

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio> sigat-durazno-api

cd sigat-durazno-api
```

### 2. Crear el entorno virtual

**Windows:**

```powershell
py -3.12 -m venv venv
```

**Linux / macOS:**

```bash
python3.12 -m venv venv
```

### 3. Activar el entorno virtual

**Windows:**

```powershell
venv\Scripts\activate
```

**Linux / macOS:**

```bash
source venv/bin/activate
```

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

Para instalar las herramientas de desarrollo:

```bash
pip install -r requirements-dev.txt
```

### 5. Configurar las variables de entorno

Crear un archivo `.env` a partir del ejemplo:

**Windows:**

```powershell
Copy-Item .env.example .env
```

**Linux / macOS:**

```bash
cp .env.example .env
```

Configurar los valores correspondientes al entorno local, incluyendo la conexión a la base de datos y los parámetros de seguridad.

Para generar un secreto aleatorio destinado a la firma de tokens:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

No publiques el archivo `.env` ni compartas sus credenciales.

### 6. Preparar la base de datos

Antes de iniciar el backend, debe estar disponible la estructura institucional de SIGAT, preparada mediante el mecanismo de instalación correspondiente.

También deben estar configurados los servicios de base de datos requeridos por el entorno.

La configuración de conexión debe corresponder a los valores definidos en el archivo `.env`.

### 7. Aplicar las migraciones del backend

Una vez preparada la estructura institucional, ejecutar:

```bash
alembic upgrade head
```

Este comando aplica las migraciones correspondientes a los componentes propios del backend.

### 8. Preparar los servicios complementarios

Configurar los servicios externos y componentes de infraestructura que requiera el entorno, de acuerdo con las variables de configuración del proyecto.

### 9. Crear el primer administrador

La creación del administrador inicial se realiza mediante la herramienta de consola:

```bash
python -m sigat_api.cli inicializar-admin --help
```

El comando permite consultar los argumentos necesarios para registrar el usuario administrador en el entorno correspondiente.

La contraseña debe configurarse de manera segura y no utilizar valores predeterminados compartidos.

### 10. Ejecutar el servidor

```bash
uvicorn sigat_api.main:app --reload --port 8000
```

El servidor estará disponible localmente en:

```text
http://localhost:8000
```

La API utiliza el prefijo:

```text
/api/v1
```

### 11. Consultar la documentación de la API

FastAPI permite consultar la documentación interactiva generada a partir del contrato OpenAPI.

**Swagger UI:**

```text
http://localhost:8000/api/v1/docs
```

**OpenAPI JSON:**

```text
http://localhost:8000/api/v1/openapi.json
```

Desde Swagger se pueden consultar los recursos documentados, sus parámetros, modelos de datos y respuestas.

---

## Pruebas y calidad del código

El proyecto incorpora herramientas para verificar la calidad, consistencia y comportamiento del backend.

### Ejecutar pruebas unitarias y de módulos

```bash
pytest -m "not integracion"
```

### Ejecutar pruebas de integración

Las pruebas de integración requieren una configuración de PostgreSQL apropiada para las bases de datos de prueba.

Configurar la variable `SIGAT_DB_URL_PRUEBAS` de acuerdo con el entorno:

```text
SIGAT_DB_URL_PRUEBAS
```

Ejecutar:

```bash
pytest -m integracion
```

### Verificar formato y estilo

```bash
ruff format src tests scripts
ruff check src tests scripts
```

### Verificar tipos

```bash
mypy
```

### Verificar dependencias entre módulos

```bash
lint-imports
```

### Generar el contrato OpenAPI

```bash
python scripts/exportar_openapi.py
```

El contrato generado se encuentra en:

```text
contracts/openapi.json
```

---

## Comandos útiles

| Comando | Función |
|---|---|
| `uvicorn sigat_api.main:app --reload --port 8000` | Ejecutar el servidor |
| `alembic upgrade head` | Aplicar migraciones del backend |
| `alembic history` | Consultar historial de migraciones |
| `alembic current` | Consultar revisión aplicada |
| `pytest -m "not integracion"` | Ejecutar pruebas sin integración |
| `pytest -m integracion` | Ejecutar pruebas de integración |
| `ruff check src tests scripts` | Revisar el código |
| `ruff format src tests scripts` | Formatear el código |
| `mypy` | Revisar tipos |
| `lint-imports` | Revisar dependencias entre módulos |
| `python scripts/exportar_openapi.py` | Generar el contrato OpenAPI |

---

## Convenciones de desarrollo

Para mantener una organización consistente, el proyecto sigue estos criterios:

1. **Separación modular:** cada módulo mantiene responsabilidades definidas.
2. **Separación por capas:** la API, los módulos, la infraestructura y los componentes compartidos conservan responsabilidades diferenciadas.
3. **Validación:** las entradas y salidas utilizan esquemas de validación.
4. **Seguridad:** la identidad y los permisos se verifican en el servidor.
5. **Manejo de errores:** las respuestas utilizan un formato estructurado.
6. **Migraciones controladas:** los cambios de estructura se incorporan mediante revisiones nuevas.
7. **Contrato actualizado:** los cambios en la interfaz de la API deben reflejarse en su contrato OpenAPI.
8. **Protección de información:** no se deben incorporar credenciales, secretos ni datos personales reales al repositorio.

---

## Flujo de trabajo con Git

El proyecto utiliza un flujo de trabajo basado en ramas para organizar la colaboración.

| Rama | Propósito |
|---|---|
| `main` | Rama principal con versiones aprobadas. |
| `develop` | Integración del trabajo del equipo. |
| `feature/*` | Desarrollo de cambios específicos. |

### Flujo recomendado

1. Actualizar la rama de trabajo.
2. Crear una rama para la tarea.
3. Realizar los cambios correspondientes.
4. Ejecutar las pruebas y verificaciones de calidad.
5. Crear un Pull Request.
6. Revisar y aprobar los cambios.
7. Integrar las modificaciones según las reglas del repositorio.

No se recomienda utilizar `git push --force` en ramas compartidas.

Las pautas adicionales se encuentran en `CONTRIBUTING.md`.

---

## Documentación del proyecto

| Archivo | Descripción |
|---|---|
| `ARCHITECTURE.md` | Organización y arquitectura general del backend. |
| `CONTRIBUTING.md` | Guía de contribución y flujo de trabajo. |
| `SECURITY.md` | Información de seguridad y reporte de vulnerabilidades. |
| `bd/CAMBIOS.md` | Convenciones y documentación de cambios de base de datos. |
| `migrations/README.md` | Información sobre las migraciones del backend. |
| `contracts/openapi.json` | Contrato de la API. |

---

## Integración con las aplicaciones cliente

Los clientes de SIGAT consumen los servicios del backend mediante solicitudes HTTP.

### SIGAT Web

La aplicación web utiliza la API para enviar solicitudes, consultar información y realizar operaciones según los permisos del usuario autenticado.

### SIGAT Móvil

La aplicación móvil utiliza los servicios de la API para intercambiar información con el sistema y apoyar las actividades realizadas desde dispositivos de campo.

### Formato de comunicación

- Protocolo: HTTP/HTTPS.
- Formato de intercambio: JSON.
- Autenticación: Bearer Token.
- Prefijo de API: `/api/v1`.
- Documentación: OpenAPI / Swagger.

---

## Proyecto SIGAT

**SIGAT — Sistema de Información para la Gestión y Análisis de la Vigilancia Fitosanitaria.**

Plataforma tecnológica orientada a apoyar la gestión, consulta, seguimiento y análisis de información relacionada con la vigilancia fitosanitaria del cultivo de durazno.

**Tecnologías principales:** Python · FastAPI · PostgreSQL · PostGIS · SQLAlchemy · Alembic · Docker.
