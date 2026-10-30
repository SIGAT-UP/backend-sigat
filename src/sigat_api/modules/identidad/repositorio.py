"""Acceso a datos de identidad. SQL contra el esquema ``sigat`` y ``api``.

El hash de la contraseña (``usua_contrasena``) solo sale de aquí hacia el servicio
de autenticación; nunca llega a una respuesta HTTP ni a un log.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from sigat_api.compartido.errores import NoImplementado
from sigat_api.infra.db.sesion import transaccion

# Columnas comunes de la sesión de un usuario (persona + rol + estado + fila hija del rol).
_SELECT_USUARIO = """
SELECT u.usua_id, u.usua_usuario, u.usua_contrasena, u.usua_proveedor, u.usua_requiere_reinicio,
       u.usua_eliminado_en, p.pers_cc, p.pers_nombre, p.pers_apellido, p.pers_correo,
       r.rol_codigo, r.rol_descripcion, e.esta_descripcion AS estado,
       CASE r.rol_codigo
         WHEN 'ADMINISTRADOR' THEN EXISTS (SELECT 1 FROM sigat.administrador a WHERE a.pers_cc = u.pers_cc)
         WHEN 'TECNICO' THEN EXISTS (SELECT 1 FROM sigat.tecnico t WHERE t.pers_cc = u.pers_cc)
         WHEN 'PRODUCTOR' THEN EXISTS (SELECT 1 FROM sigat.productor pr WHERE pr.pers_cc = u.pers_cc)
         ELSE true
       END AS rol_coherente,
       (SELECT pd.pred_nombre FROM sigat.predio pd WHERE pd.pers_cc = u.pers_cc
         ORDER BY pd.pred_nombre LIMIT 1) AS predio_nombre,
       (SELECT count(*) FROM sigat.predio pd WHERE pd.pers_cc = u.pers_cc) AS predios
  FROM sigat.usuario u
  JOIN sigat.persona p ON p.pers_cc = u.pers_cc
  JOIN sigat.rol r ON r.rol_id = u.rol_id
  JOIN sigat.estado_registro e ON e.esta_id = u.esta_id
"""


class RepositorioIdentidad:
    def __init__(self, con: AsyncConnection) -> None:
        self._con = con

    # ------------------------------------------------------------ autenticación
    async def fijar_actor(self, usua_id: int) -> None:
        """``SET LOCAL sigat.usuario_actual``: quien entra es el autor de sus propias escrituras
        (último acceso, dispositivo, bitácora)."""
        await self._con.execute(
            text("SELECT set_config('sigat.usuario_actual', :u, true)"), {"u": str(usua_id)}
        )

    async def buscar_para_login(self, usuario_o_correo: str) -> dict[str, Any] | None:
        """Coincidencia sin distinguir mayúsculas contra ``usua_usuario`` o ``pers_correo``.

        EXCLUYE los usuarios dados de baja (``usua_eliminado_en``, BD v9). Si el texto
        coincide con el usuario de una cuenta y el correo de otra, gana el usuario.
        """
        fila = (
            (
                await self._con.execute(
                    text(
                        _SELECT_USUARIO
                        + """
 WHERE u.usua_eliminado_en IS NULL
   AND (lower(u.usua_usuario) = :v OR lower(p.pers_correo) = :v)
 ORDER BY (lower(u.usua_usuario) = :v) DESC
 LIMIT 1"""
                    ),
                    {"v": usuario_o_correo.strip().lower()},
                )
            )
            .mappings()
            .first()
        )
        return dict(fila) if fila else None

    async def usuario_por_id(self, usua_id: int) -> dict[str, Any] | None:
        fila = (
            (
                await self._con.execute(
                    text(_SELECT_USUARIO + " WHERE u.usua_id = :u AND u.usua_eliminado_en IS NULL"),
                    {"u": usua_id},
                )
            )
            .mappings()
            .first()
        )
        return dict(fila) if fila else None

    async def registrar_acceso(self, usua_id: int, momento: datetime, nuevo_hash: str | None = None) -> None:
        """Último acceso (columna mutable, auditada por fn_auditar). Si el hash de la
        contraseña usa parámetros viejos, se guarda el nuevo en la misma sentencia."""
        if nuevo_hash:
            await self._con.execute(
                text(
                    "UPDATE sigat.usuario SET usua_ultimo_acceso = :m, usua_contrasena = :h"
                    " WHERE usua_id = :u"
                ),
                {"m": momento, "h": nuevo_hash, "u": usua_id},
            )
        else:
            await self._con.execute(
                text("UPDATE sigat.usuario SET usua_ultimo_acceso = :m WHERE usua_id = :u"),
                {"m": momento, "u": usua_id},
            )

    # ------------------------------------------------------------ intentos de inicio de sesión
    async def fallos_recientes(self, clave: str, desde: datetime) -> int:
        """Fallos de ``clave`` (usuario normalizado o IP) desde el último éxito y dentro de la ventana."""
        valor = await self._con.scalar(
            text(
                """
SELECT count(*) FROM api.intento_login i
 WHERE i.inte_clave = :c AND NOT i.inte_exito AND i.inte_t >= :desde
   AND i.inte_t > coalesce((SELECT max(x.inte_t) FROM api.intento_login x
                             WHERE x.inte_clave = :c AND x.inte_exito), '-infinity')"""
            ),
            {"c": clave, "desde": desde},
        )
        return int(valor or 0)

    async def registrar_intento(self, claves: list[str], exito: bool) -> None:
        """Se guarda en una transacción PROPIA: un fallo debe quedar registrado aunque la
        petición termine en error (y su transacción se revierta)."""
        async with transaccion(None) as con:
            for clave in claves:
                await con.execute(
                    text("INSERT INTO api.intento_login (inte_clave, inte_exito) VALUES (:c, :e)"),
                    {"c": clave[:300], "e": exito},
                )

    async def depurar_intentos(self, antes_de: datetime) -> None:
        """Mantenimiento: borra intentos viejos (tabla técnica, no es historia del negocio)."""
        await self._con.execute(text("DELETE FROM api.intento_login WHERE inte_t < :t"), {"t": antes_de})

    # ------------------------------------------------------------ sesiones de refresco
    async def guardar_sesion_refresco(
        self,
        usua_id: int,
        disp_id: UUID,
        hash_token: str,
        familia: UUID,
        expira: datetime,
        cliente: str,
    ) -> None:
        await self._con.execute(
            text(
                """
INSERT INTO api.sesion_refresco (usua_id, disp_id, sesr_familia, sesr_hash, sesr_cliente, sesr_expira_en)
VALUES (:u, :d, :f, :h, :c, :e)"""
            ),
            {"u": usua_id, "d": disp_id, "f": familia, "h": hash_token, "c": cliente, "e": expira},
        )

    async def consumir_sesion_refresco(self, hash_token: str, ahora: datetime) -> dict[str, Any] | None:
        """Marca usada la sesión (una sola vez) y la devuelve con ``estado``:

        * ``valida``: se acaba de consumir; se puede emitir el par nuevo.
        * ``revocada``: se cerró (logout, cambio de contraseña); no se puede usar.
        * ``reutilizada``: ya se había usado = posible robo. Se revoca TODA la familia en una
          transacción propia, para que la revocación quede aunque la petición termine en 401.

        Devuelve ``None`` si el token no existe.
        """
        fila = (
            (
                await self._con.execute(
                    text(
                        """
SELECT sesr_id, usua_id, disp_id, sesr_familia, sesr_cliente, sesr_expira_en,
       sesr_usado_en, sesr_revocado_en
  FROM api.sesion_refresco WHERE sesr_hash = :h"""
                    ),
                    {"h": hash_token},
                )
            )
            .mappings()
            .first()
        )
        if fila is None:
            return None
        datos = dict(fila)
        if datos["sesr_revocado_en"] is not None and datos["sesr_usado_en"] is None:
            datos["estado"] = "revocada"
            return datos
        reclamada = None
        if datos["sesr_usado_en"] is None:
            # Reclamo atómico: si dos peticiones llegan a la vez, solo una lo consigue.
            reclamada = await self._con.scalar(
                text(
                    "UPDATE api.sesion_refresco SET sesr_usado_en = :t"
                    " WHERE sesr_id = :i AND sesr_usado_en IS NULL AND sesr_revocado_en IS NULL"
                    " RETURNING sesr_id"
                ),
                {"t": ahora, "i": datos["sesr_id"]},
            )
        if reclamada is not None:
            datos["estado"] = "valida"
            return datos
        async with transaccion(None) as con:
            await con.execute(
                text(
                    "UPDATE api.sesion_refresco SET sesr_revocado_en = :t"
                    " WHERE sesr_familia = :f AND sesr_revocado_en IS NULL"
                ),
                {"t": ahora, "f": datos["sesr_familia"]},
            )
        datos["estado"] = "reutilizada"
        return datos

    async def revocar_sesiones(
        self,
        usua_id: int,
        ahora: datetime,
        disp_id: UUID | None = None,
        excepto_disp: UUID | None = None,
    ) -> None:
        """Revoca las sesiones de refresco vigentes del usuario: de un dispositivo, de todos o de todos
        menos uno. Revocar también invalida al instante los tokens de acceso ya emitidos
        (ver ``infra.db.sesion``)."""
        await self._con.execute(
            text(
                """
UPDATE api.sesion_refresco SET sesr_revocado_en = :t
 WHERE usua_id = :u AND sesr_revocado_en IS NULL AND sesr_usado_en IS NULL
   AND (CAST(:d AS uuid) IS NULL OR disp_id = CAST(:d AS uuid))
   AND (CAST(:x AS uuid) IS NULL OR disp_id <> CAST(:x AS uuid))"""
            ),
            {
                "t": ahora,
                "u": usua_id,
                "d": str(disp_id) if disp_id else None,
                "x": str(excepto_disp) if excepto_disp else None,
            },
        )

    # ------------------------------------------------------------ restablecimiento de contraseña
    async def crear_restablecimiento(self, usua_id: int, hash_token: str, expira: datetime) -> int:
        """INSERT restablecimiento_clave (solo el SHA-256 del token). Devuelve ``rest_id``."""
        rest_id = await self._con.scalar(
            text(
                "INSERT INTO sigat.restablecimiento_clave (usua_id, rest_token_hash, rest_expira_en)"
                " VALUES (:u, :h, :e) RETURNING rest_id"
            ),
            {"u": usua_id, "h": hash_token, "e": expira},
        )
        return int(rest_id)

    async def usar_restablecimiento(self, hash_token: str, ahora: datetime) -> int | None:
        """Valida vigencia y uso único (rest_usado_en IS NULL); lo marca usado y devuelve usua_id."""
        valor = await self._con.scalar(
            text(
                """
UPDATE sigat.restablecimiento_clave SET rest_usado_en = :t
 WHERE rest_token_hash = :h AND rest_usado_en IS NULL AND rest_expira_en > :t
RETURNING usua_id"""
            ),
            {"h": hash_token, "t": ahora},
        )
        return int(valor) if valor is not None else None

    async def actualizar_contrasena(self, usua_id: int, hash_contrasena: str) -> None:
        """Nueva contraseña (solo hash) y fin de la marca de reinicio obligatorio."""
        await self._con.execute(
            text(
                "UPDATE sigat.usuario SET usua_contrasena = :h, usua_requiere_reinicio = false"
                " WHERE usua_id = :u"
            ),
            {"h": hash_contrasena, "u": usua_id},
        )

    async def perfil(self, usua_id: int) -> dict[str, Any] | None:
        fila = (
            (
                await self._con.execute(
                    text(
                        """
SELECT u.usua_id, p.pers_nombre || ' ' || p.pers_apellido AS nombre, u.usua_usuario, p.pers_correo,
       p.pers_telefono, r.rol_codigo, r.rol_descripcion, pf.arch_id_foto, pf.perf_actualizado_en
  FROM sigat.usuario u
  JOIN sigat.persona p ON p.pers_cc = u.pers_cc
  JOIN sigat.rol r ON r.rol_id = u.rol_id
  LEFT JOIN sigat.perfil_usuario pf ON pf.usua_id = u.usua_id
 WHERE u.usua_id = :u AND u.usua_eliminado_en IS NULL"""
                    ),
                    {"u": usua_id},
                )
            )
            .mappings()
            .first()
        )
        return dict(fila) if fila else None

    async def predios_accesibles(self, usua_id: int, global_: bool) -> list[dict[str, Any]]:
        """``v_acceso_predio`` (asignación vigente o propiedad). El ADMINISTRADOR (ámbito global) ve todos."""
        if global_:
            sql = "SELECT pred_id, pred_nombre, 'global' AS origen FROM sigat.predio ORDER BY pred_nombre"
        else:
            sql = """
SELECT DISTINCT ON (p.pred_id) p.pred_id, p.pred_nombre, a.origen
  FROM sigat.v_acceso_predio a JOIN sigat.predio p ON p.pred_id = a.pred_id
 WHERE a.usua_id = :u
 ORDER BY p.pred_id, a.origen"""
        filas = await self._con.execute(text(sql), {"u": usua_id})
        return [dict(f) for f in filas.mappings()]

    # ------------------------------------------------------------ administración de usuarios
    async def roles(self) -> list[dict[str, Any]]:
        filas = await self._con.execute(
            text("SELECT rol_id, rol_codigo, rol_descripcion, rol_ambito FROM sigat.rol ORDER BY rol_id")
        )
        return [dict(f) for f in filas.mappings()]

    async def listar_usuarios(
        self, filtro_rol: str | None, activo: bool | None, despues_de: int | None, limite: int
    ) -> list[dict[str, Any]]:
        """``v_usuario_admin`` (excluye eliminados), en orden de ``usua_id``."""
        filas = await self._con.execute(
            text(
                """
SELECT * FROM sigat.v_usuario_admin
 WHERE (CAST(:rol AS text) IS NULL OR rol_codigo = CAST(:rol AS text))
   AND (CAST(:activo AS boolean) IS NULL OR activo = CAST(:activo AS boolean))
   AND (CAST(:despues AS integer) IS NULL OR usua_id > CAST(:despues AS integer))
 ORDER BY usua_id
 LIMIT :lim"""
            ),
            {"rol": filtro_rol, "activo": activo, "despues": despues_de, "lim": limite},
        )
        return [dict(f) for f in filas.mappings()]

    async def usuario_admin(self, usua_id: int) -> dict[str, Any] | None:
        fila = (
            (
                await self._con.execute(
                    text("SELECT * FROM sigat.v_usuario_admin WHERE usua_id = :u"), {"u": usua_id}
                )
            )
            .mappings()
            .first()
        )
        return dict(fila) if fila else None

    async def estado_cuenta(self, usua_id: int) -> dict[str, Any] | None:
        """Datos mínimos para decidir (incluye eliminados, para responder 409 y no 404)."""
        fila = (
            (
                await self._con.execute(
                    text(
                        """
SELECT u.usua_id, u.pers_cc, u.usua_proveedor, u.usua_eliminado_en, r.rol_codigo,
       e.esta_descripcion AS estado
  FROM sigat.usuario u JOIN sigat.rol r ON r.rol_id = u.rol_id
  JOIN sigat.estado_registro e ON e.esta_id = u.esta_id
 WHERE u.usua_id = :u"""
                    ),
                    {"u": usua_id},
                )
            )
            .mappings()
            .first()
        )
        return dict(fila) if fila else None

    async def administradores_activos(self, excepto: int | None = None) -> list[int]:
        filas = await self._con.execute(
            text(
                """
SELECT u.usua_id FROM sigat.usuario u
  JOIN sigat.rol r ON r.rol_id = u.rol_id
  JOIN sigat.estado_registro e ON e.esta_id = u.esta_id
 WHERE r.rol_codigo = 'ADMINISTRADOR' AND e.esta_descripcion = 'activo'
   AND u.usua_eliminado_en IS NULL
   AND (CAST(:excepto AS integer) IS NULL OR u.usua_id <> CAST(:excepto AS integer))
 ORDER BY u.usua_id"""
            ),
            {"excepto": excepto},
        )
        return [int(f[0]) for f in filas]

    async def crear_usuario(self, datos: dict[str, Any]) -> int:
        """En la transacción actual: persona -> fila de rol -> usuario -> perfil.

        ``datos``: pers_cc, nombre, apellido, correo, telefono, direccion, usuario,
        hash_contrasena (o None: queda con usua_requiere_reinicio), rol (código),
        cent_id (ADMINISTRADOR/TECNICO), tecn_codigo (TECNICO, opcional), muni_id (PRODUCTOR),
        registrado_por (usua_id o None). Las restricciones de la BD validan formato,
        unicidad (usuario y correo sin distinguir mayúsculas) y coherencia del rol.
        """
        rol = str(datos["rol"])
        await self._con.execute(
            text(
                """
INSERT INTO sigat.persona (pers_cc, pers_nombre, pers_apellido, pers_correo, pers_telefono, pers_direccion)
VALUES (:cc, :n, :a, :c, :t, :d)"""
            ),
            {
                "cc": datos["pers_cc"],
                "n": datos["nombre"],
                "a": datos["apellido"],
                "c": datos.get("correo"),
                "t": datos.get("telefono"),
                "d": datos.get("direccion"),
            },
        )
        await self._crear_fila_rol(int(datos["pers_cc"]), rol, datos)
        hash_contrasena = datos.get("hash_contrasena")
        usua_id = await self._con.scalar(
            text(
                """
INSERT INTO sigat.usuario (pers_cc, usua_usuario, usua_contrasena, usua_requiere_reinicio, rol_id, esta_id)
VALUES (:cc, :u, :h, :reinicio,
        (SELECT rol_id FROM sigat.rol WHERE rol_codigo = :r),
        (SELECT esta_id FROM sigat.estado_registro WHERE esta_descripcion = 'activo'))
RETURNING usua_id"""
            ),
            {
                "cc": datos["pers_cc"],
                "u": datos["usuario"],
                "h": hash_contrasena,
                "reinicio": hash_contrasena is None or bool(datos.get("requiere_reinicio", False)),
                "r": rol,
            },
        )
        await self._con.execute(
            text("INSERT INTO sigat.perfil_usuario (usua_id) VALUES (:u)"), {"u": usua_id}
        )
        return int(usua_id)

    async def _crear_fila_rol(self, pers_cc: int, rol: str, datos: dict[str, Any]) -> None:
        """Fila hija que exige la BD según el rol (si aún no existe para esa persona)."""
        if rol == "ADMINISTRADOR":
            await self._con.execute(
                text(
                    "INSERT INTO sigat.administrador (pers_cc, cent_id) SELECT :cc, :cen"
                    " WHERE NOT EXISTS (SELECT 1 FROM sigat.administrador WHERE pers_cc = :cc)"
                ),
                {"cc": pers_cc, "cen": datos["cent_id"]},
            )
        elif rol == "TECNICO":
            await self._con.execute(
                text(
                    """
INSERT INTO sigat.tecnico (pers_cc, cent_id, admi_id, tecn_codigo, tecn_fecha_registro, esta_id)
SELECT :cc, :cen,
       coalesce((SELECT a.admi_id FROM sigat.administrador a JOIN sigat.usuario u ON u.pers_cc = a.pers_cc
                  WHERE u.usua_id = :por),
                (SELECT min(admi_id) FROM sigat.administrador)),
       :cod, current_date,
       (SELECT esta_id FROM sigat.estado_registro WHERE esta_descripcion = 'activo')
 WHERE NOT EXISTS (SELECT 1 FROM sigat.tecnico WHERE pers_cc = :cc)"""
                ),
                {
                    "cc": pers_cc,
                    "cen": datos["cent_id"],
                    "por": datos.get("registrado_por"),
                    "cod": datos.get("tecn_codigo"),
                },
            )
        elif rol == "PRODUCTOR":
            await self._con.execute(
                text(
                    "INSERT INTO sigat.productor (pers_cc, prod_fecha_registro, muni_id, prod_usua_registro_id)"
                    " SELECT :cc, current_date, :mun, :por"
                    " WHERE NOT EXISTS (SELECT 1 FROM sigat.productor WHERE pers_cc = :cc)"
                ),
                {"cc": pers_cc, "mun": datos["muni_id"], "por": datos.get("registrado_por")},
            )

    async def actualizar_usuario(
        self, usua_id: int, persona: dict[str, Any], usuario: dict[str, Any]
    ) -> None:
        """Solo las columnas recibidas. ``persona``: pers_nombre, pers_apellido, pers_correo,
        pers_telefono, pers_direccion. ``usuario``: usua_usuario, rol (código), datos_rol."""
        columnas_persona = {
            k: v
            for k, v in persona.items()
            if k in ("pers_nombre", "pers_apellido", "pers_correo", "pers_telefono", "pers_direccion")
        }
        if columnas_persona:
            asignaciones = ", ".join(f"{k} = :{k}" for k in columnas_persona)  # nombres fijos de la lista
            await self._con.execute(
                text(
                    f"UPDATE sigat.persona SET {asignaciones}"  # noqa: S608
                    " WHERE pers_cc = (SELECT pers_cc FROM sigat.usuario WHERE usua_id = :usua)"
                ),
                {**columnas_persona, "usua": usua_id},
            )
        if "usua_usuario" in usuario:
            await self._con.execute(
                text("UPDATE sigat.usuario SET usua_usuario = :v WHERE usua_id = :u"),
                {"v": usuario["usua_usuario"], "u": usua_id},
            )
        if "rol" in usuario:
            pers_cc = await self._con.scalar(
                text("SELECT pers_cc FROM sigat.usuario WHERE usua_id = :u"), {"u": usua_id}
            )
            await self._crear_fila_rol(int(pers_cc), str(usuario["rol"]), usuario.get("datos_rol") or {})
            await self._con.execute(
                text(
                    "UPDATE sigat.usuario SET rol_id = (SELECT rol_id FROM sigat.rol WHERE rol_codigo = :r)"
                    " WHERE usua_id = :u"
                ),
                {"r": usuario["rol"], "u": usua_id},
            )

    async def corregir_cedula(self, usua_id: int, nueva: int) -> None:
        await self._con.execute(
            text("SELECT sigat.fn_corregir_cedula(:u, CAST(:n AS bigint))"), {"u": usua_id, "n": nueva}
        )

    async def tiene_actividad(self, usua_id: int) -> bool:
        return bool(
            await self._con.scalar(text("SELECT sigat.fn_usuario_tiene_actividad(:u)"), {"u": usua_id})
        )

    async def eliminar_usuario(self, usua_id: int, motivo: str) -> str:
        return str(
            await self._con.scalar(
                text("SELECT sigat.fn_eliminar_usuario(:u, :m)"), {"u": usua_id, "m": motivo}
            )
        )

    async def cambiar_estado(self, usua_id: int, activo: bool) -> None:
        await self._con.execute(
            text(
                "UPDATE sigat.usuario SET esta_id = (SELECT esta_id FROM sigat.estado_registro"
                " WHERE esta_descripcion = :e) WHERE usua_id = :u"
            ),
            {"e": "activo" if activo else "inactivo", "u": usua_id},
        )

    async def asignar_contrasena(
        self, usua_id: int, hash_contrasena: str, exigir_cambio: bool, ahora: datetime
    ) -> None:
        """Contraseña asignada por el administrador. Cierra las solicitudes de restablecimiento
        pendientes de ese usuario (quedan como usadas)."""
        await self._con.execute(
            text(
                "UPDATE sigat.usuario SET usua_contrasena = :h, usua_requiere_reinicio = :r WHERE usua_id = :u"
            ),
            {"h": hash_contrasena, "r": exigir_cambio, "u": usua_id},
        )
        await self._con.execute(
            text(
                "UPDATE sigat.restablecimiento_clave SET rest_usado_en = :t"
                " WHERE usua_id = :u AND rest_usado_en IS NULL"
            ),
            {"t": ahora, "u": usua_id},
        )

    async def solicitud_reciente(self, usua_id: int, desde: datetime) -> bool:
        """¿Ya hay una solicitud de restablecimiento sin atender desde ``desde``? (evita avisos repetidos)."""
        return bool(
            await self._con.scalar(
                text(
                    "SELECT EXISTS (SELECT 1 FROM sigat.restablecimiento_clave"
                    " WHERE usua_id = :u AND rest_usado_en IS NULL AND rest_solicitado_en >= :d)"
                ),
                {"u": usua_id, "d": desde},
            )
        )

    async def asignaciones(self, usua_id: int) -> list[dict[str, Any]]:
        raise NoImplementado("Asignaciones de predio")
