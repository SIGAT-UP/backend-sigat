"""VALIDADOR DE INVARIANTES (Arquitectura §6.3). Descarta lo mal formado ANTES de tocar el historico.

Se valida en el cliente la FORMA y aquí, otra vez, el DOMINIO (§5.3): el dispositivo
puede estar desactualizado respecto a la configuración vigente.
"""

from datetime import datetime

from sigat_api.compartido.contratos import OperacionCampo
from sigat_api.compartido.errores import NoImplementado
from sigat_api.modules.registro.dominio import MotivoRechazo
from sigat_api.modules.registro.puertos import PuertoConfiguracion
from sigat_api.modules.registro.repositorio import RepositorioRegistro


class ValidadorInvariantes:
    def __init__(self, configuracion: PuertoConfiguracion, repo: RepositorioRegistro) -> None:
        self._configuracion = configuracion
        self._repo = repo  # periodo_trampeo es de este módulo

    async def validar(self, op: OperacionCampo, ahora_servidor: datetime) -> MotivoRechazo | None:
        """Devuelve el primer motivo de rechazo o None.

        Por entidad (mínimo):
        * Todas: t_observacion <= t_captura <= ahora + tolerancia; linaje permitido para el rol
          (TECNICO -> inspeccion_oficial, PRODUCTOR -> autorreporte); el lote es visible para el actor.
        * lectura_trampa: la trampa pertenecía al lote en t_observacion; el lote estaba activo;
          t_observacion dentro de un periodo de trampeo del lote; especímenes >= 0 y nulos si
          lect_leida = false; justificación obligatoria si no se leyó; la visita existe
          (o vino antes en el mismo lote de operaciones).
        * aplicacion_fitosanitaria: producto de catálogo o texto; dosis/área > 0 con unidad.
        * cosecha: volúmenes >= 0; fecha real no anterior a la esperada sin observación.
        * planificacion_lote: solo el técnico destinatario; no_ejecutada exige justificación.
        """
        raise NoImplementado("Validación de invariantes")
