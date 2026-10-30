"""Token de acceso (JWT) y token de refresco opaco."""

import os
from datetime import UTC, datetime
from uuid import uuid4

import jwt
import pytest
from pydantic import SecretStr

from sigat_api.compartido.errores import NoAutenticado
from sigat_api.compartido.tipos import Cliente, RolCodigo
from sigat_api.config import Configuracion
from sigat_api.infra.seguridad.tokens import ServicioTokens, hash_refresco


def _cfg(**extra: object) -> Configuracion:
    return Configuracion(jwt_secreto=SecretStr(os.environ["SIGAT_JWT_SECRETO"]), **extra)  # type: ignore[arg-type]


def test_emite_y_verifica_el_acceso() -> None:
    t = ServicioTokens(_cfg())
    disp = uuid4()
    token, vida = t.emitir_acceso(7, RolCodigo.PRODUCTOR, disp, Cliente.MOVIL)
    r = t.verificar_acceso(token)
    assert (r.usua_id, r.rol, r.disp_id, r.cliente) == (7, RolCodigo.PRODUCTOR, disp, Cliente.MOVIL)
    assert vida == 15 * 60
    assert r.expira > datetime.now(UTC)


def test_token_vencido_da_token_vencido() -> None:
    cfg = _cfg()
    vencido = jwt.encode(
        {
            "sub": "1",
            "rol": "TECNICO",
            "cli": "movil",
            "jti": "x",
            "iat": 1,
            "exp": 2,
            "iss": cfg.jwt_emisor,
            "aud": cfg.jwt_audiencia,
        },
        cfg.jwt_secreto.get_secret_value(),
        algorithm="HS256",
    )
    with pytest.raises(NoAutenticado) as err:
        ServicioTokens(cfg).verificar_acceso(vencido)
    assert err.value.codigo == "TOKEN_VENCIDO"


def test_otra_firma_o_audiencia_no_sirve() -> None:
    token, _ = ServicioTokens(_cfg()).emitir_acceso(1, RolCodigo.TECNICO, None, Cliente.WEB)
    with pytest.raises(NoAutenticado):
        ServicioTokens(_cfg(jwt_audiencia="otra")).verificar_acceso(token)
    otro = Configuracion(jwt_secreto=SecretStr("z" * 64))
    with pytest.raises(NoAutenticado):
        ServicioTokens(otro).verificar_acceso(token)


def test_secreto_corto_impide_arrancar_tokens() -> None:
    with pytest.raises(RuntimeError, match="SIGAT_JWT_SECRETO"):
        ServicioTokens(Configuracion(jwt_secreto=SecretStr("corto"))).emitir_acceso(
            1, RolCodigo.TECNICO, None, Cliente.WEB
        )


def test_refresco_es_opaco_y_solo_se_guarda_su_hash() -> None:
    claro, huella = ServicioTokens(_cfg()).nuevo_refresco()
    assert len(claro) >= 60
    assert "." not in claro
    assert huella == hash_refresco(claro)
    assert len(huella) == 64
