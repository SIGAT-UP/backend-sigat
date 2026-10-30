"""Casos de uso del catálogo."""

from sigat_api.compartido.errores import NoEncontrado, NoImplementado
from sigat_api.compartido.tipos import Actor
from sigat_api.infra.cola.cola import Cola
from sigat_api.modules.catalogo import esquemas as e
from sigat_api.modules.catalogo.dominio import CATALOGOS, POR_CODIGO
from sigat_api.modules.catalogo.repositorio import RepositorioCatalogo


class ServicioCatalogo:
    def __init__(self, repo: RepositorioCatalogo, cola: Cola) -> None:
        self._repo = repo
        self._cola = cola

    async def listar(self, actor: Actor) -> list[e.CatalogoInfo]:
        tarjetas = []
        for cat in CATALOGOS:
            items = await self.items(actor, cat.codigo, incluir_inactivos=False)
            nombres = ", ".join(i.descripcion for i in items[:4]) + ("…" if len(items) > 4 else "")
            tarjetas.append(
                e.CatalogoInfo(
                    codigo=cat.codigo,
                    titulo=cat.titulo,
                    editable=cat.editable,
                    total_items=len(items),
                    resumen=f"{len(items)} valores: {nombres}" if items else "Sin valores",
                )
            )
        return tarjetas

    async def items(self, actor: Actor, codigo: str, incluir_inactivos: bool) -> list[e.ItemCatalogo]:
        """404 si ``codigo`` no está en ``dominio.POR_CODIGO``. Columnas: ``<prefijo>_id``,
        ``<prefijo>_descripcion``, ``<prefijo>_codigo`` (si existe), la de activo y el resto en atributos."""
        cat = POR_CODIGO.get(codigo)
        if cat is None:
            raise NoEncontrado("Ese catálogo no existe.", codigo="CATALOGO_NO_ENCONTRADO")
        resultado = []
        for fila in await self._repo.items(cat, incluir_inactivos):
            # El texto visible está en _descripcion en casi todos; en algunos en _nombre o _titulo.
            col_texto = next(
                (
                    f"{cat.prefijo}_{c}"
                    for c in ("descripcion", "nombre", "titulo")
                    if f"{cat.prefijo}_{c}" in fila
                ),
                f"{cat.prefijo}_descripcion",
            )
            fijas = {f"{cat.prefijo}_id", col_texto, f"{cat.prefijo}_codigo", cat.columna_activo}
            resultado.append(
                e.ItemCatalogo(
                    id=int(fila[f"{cat.prefijo}_id"]),
                    descripcion=str(fila.get(col_texto) or ""),
                    codigo=fila.get(f"{cat.prefijo}_codigo"),
                    activo=bool(fila[cat.columna_activo]) if cat.columna_activo else True,
                    atributos={k: _json(v) for k, v in fila.items() if k not in fijas},
                )
            )
        return resultado

    async def reemplazar(self, actor: Actor, codigo: str, s: e.ReemplazoCatalogo) -> e.CatalogoInfo:
        """Reglas (web): sin repetidos (sin distinguir mayúsculas), al menos un valor.
        Ausente y en uso -> se retira (activo=false); si el catálogo no admite retiro
        y el valor está en uso -> 409 ``VALOR_EN_USO``. Invalida los paquetes de campo
        (tarea ``generar_paquete_campo``) porque el móvil trae los catálogos precargados."""
        raise NoImplementado("Guardar catálogo")

    async def departamentos(self) -> list[e.Departamento]:
        return [e.Departamento(**f) for f in await self._repo.departamentos()]

    async def municipios(self, depa_id: int | None) -> list[e.Municipio]:
        return [e.Municipio(**f) for f in await self._repo.municipios(depa_id)]


def _json(valor: object) -> object:
    """Valores aptos para JSON (números con decimales y fechas como texto)."""
    if valor is None or isinstance(valor, bool | int | float | str):
        return valor
    return str(valor)
