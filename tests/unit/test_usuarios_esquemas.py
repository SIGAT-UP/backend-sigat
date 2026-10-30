"""Validaciones de forma del alta y la edición de usuarios (mismas exigencias que la BD v9)."""

import pytest
from pydantic import ValidationError

from sigat_api.compartido.tipos import RolCodigo
from sigat_api.modules.identidad.esquemas import ActualizacionUsuario, EliminacionUsuario, NuevoUsuario

BASE = {"pers_cc": 1098765432, "nombre": "Ana", "apellido": "Pérez", "usuario": "aperez"}


@pytest.mark.regla
def test_tecnico_exige_centro_de_acopio() -> None:
    with pytest.raises(ValidationError, match="centro de acopio"):
        NuevoUsuario(**BASE, rol=RolCodigo.TECNICO)
    assert NuevoUsuario(**BASE, rol=RolCodigo.TECNICO, datos_rol={"cent_id": 1}).datos_rol.cent_id == 1


@pytest.mark.regla
def test_productor_exige_municipio() -> None:
    with pytest.raises(ValidationError, match="municipio"):
        NuevoUsuario(**BASE, rol=RolCodigo.PRODUCTOR)


@pytest.mark.regla
def test_agronomo_no_exige_datos_de_rol() -> None:
    assert NuevoUsuario(**BASE, rol=RolCodigo.AGRONOMO_SUPERVISOR).rol is RolCodigo.AGRONOMO_SUPERVISOR


@pytest.mark.regla
def test_edicion_vacia_se_rechaza_y_parcial_se_acepta() -> None:
    with pytest.raises(ValidationError, match="al menos un campo"):
        ActualizacionUsuario()
    assert ActualizacionUsuario(nombre="Ana María").model_fields_set == {"nombre"}


@pytest.mark.regla
def test_cambio_a_productor_en_edicion_exige_municipio() -> None:
    with pytest.raises(ValidationError, match="municipio"):
        ActualizacionUsuario(rol=RolCodigo.PRODUCTOR)


@pytest.mark.regla
def test_eliminar_exige_motivo_de_10_caracteres() -> None:
    with pytest.raises(ValidationError):
        EliminacionUsuario(motivo="corto")
