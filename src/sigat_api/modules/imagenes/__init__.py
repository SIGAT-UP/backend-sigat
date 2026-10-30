"""Módulo IMÁGENES Y EVIDENCIA (contenedor 6 del C4; candidato a extracción, ADR-14).

Responsabilidad: metadatos de archivos (fotos de evidencia, foto de perfil,
documentos de instrucción, imágenes de diseño), subida en dos pasos con URL
firmada, verificación de la huella SHA-256 y del tipo por CONTENIDO, y el
vínculo de la evidencia con su lectura/hallazgo/visita/actividad.

Frontera de datos: archivo_adjunto, evidencia, imagen_diseno. Binarios: almacén
de objetos (nunca la BD). ADR-12: la evidencia viaja DESPUÉS del dato numérico.
ADR-11 / RK-07: las fotos pueden contener personas; retención (UQQ-014) pendiente.
"""
