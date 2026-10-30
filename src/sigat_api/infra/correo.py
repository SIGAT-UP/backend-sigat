"""Envío de correo (recuperación de contraseña). Se ejecuta desde la cola, nunca en la petición."""

from sigat_api.compartido.errores import NoImplementado


async def enviar(destinatario: str, asunto: str, cuerpo_texto: str) -> None:
    raise NoImplementado("Envío de correo SMTP")
