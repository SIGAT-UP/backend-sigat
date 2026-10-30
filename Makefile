# Atajos de desarrollo. La autoridad es la CI.
PY ?= python

.PHONY: revisar-bd instalar ejecutar worker formato lint tipos fronteras pruebas cobertura contrato contrato-verificar tablas migrar calidad

instalar:            ## Instala dependencias de desarrollo
	$(PY) -m pip install -r requirements-dev.txt

ejecutar:            ## Levanta la API con recarga
	uvicorn sigat_api.main:app --reload --app-dir src

worker:              ## Levanta el procesador de la cola de reproceso
	$(PY) -m sigat_api.worker

formato:
	ruff format src tests scripts

lint:
	ruff check src tests scripts

tipos:
	mypy

fronteras:           ## ADR-17: falla si un módulo importa otro
	lint-imports

pruebas:
	pytest -m "not integracion"

cobertura:
	pytest --cov --cov-report=term-missing

contrato:            ## Regenera contracts/openapi.json desde el código
	$(PY) scripts/exportar_openapi.py

contrato-verificar:  ## Falla si el openapi.json versionado no coincide con el código
	$(PY) scripts/exportar_openapi.py --verificar

tablas:              ## Genera las definiciones Core de SQLAlchemy desde la BD SIGAT instalada
	sqlacodegen --generator tables --schemas sigat "$$SIGAT_DB_URL_SYNC" > src/sigat_api/infra/db/tablas_generadas.py

migrar:              ## Aplica migraciones propias del backend (esquemas api y cola)
	alembic upgrade head

revisar-bd:          ## Cambios destructivos de BD en la rama (frente a origin/main)
	python scripts/revisar_migraciones.py

calidad: lint tipos fronteras pruebas contrato-verificar
