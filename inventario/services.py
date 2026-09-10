"""Casos de uso del modulo Gastos que no encajan naturalmente en un modelo
o un formulario: aqui vive el procesamiento de la imagen del comprobante,
separado para que `models.py` y `forms.py` no mezclen esa logica."""

import io

from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

try:
    # Permite abrir fotos HEIC/HEIF (formato nativo de iPhone) con Pillow
    # como si fueran JPEG/PNG. Si el paquete no esta instalado, el resto del
    # pipeline sigue funcionando igual para los formatos ya soportados.
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:  # pragma: no cover
    pass

MAX_IMAGEN_BYTES = 5 * 1024 * 1024  # 5 MB
FORMATOS_IMAGEN_PERMITIDOS = {"JPEG", "PNG", "WEBP", "BMP", "GIF", "HEIF"}
CALIDAD_WEBP = 82
MAX_FOTOS_POR_PRODUCTO = 8
TAMANO_MAX_DISPLAY = (1600, 1600)  # lado mayor, para vista de detalle/galeria
TAMANO_MINIATURA = (320, 320)  # para listados


class ImagenInvalidaError(Exception):
    """El archivo subido no es una imagen valida o no cumple las reglas."""


def validar_imagen(archivo):
    """Valida tamano y contenido real del archivo (no solo su extension)
    antes de aceptarlo, para no procesar ni guardar algo que no sea una
    imagen legitima."""
    if archivo.size > MAX_IMAGEN_BYTES:
        raise ImagenInvalidaError("La imagen no puede superar los 5 MB.")

    try:
        with Image.open(archivo) as imagen:
            imagen.verify()
            formato = imagen.format
    except (UnidentifiedImageError, OSError) as exc:
        raise ImagenInvalidaError("El archivo no es una imagen valida.") from exc
    finally:
        archivo.seek(0)

    if formato not in FORMATOS_IMAGEN_PERMITIDOS:
        raise ImagenInvalidaError("Formato de imagen no soportado.")


def convertir_a_webp(archivo, generar_miniatura=False):
    """Convierte cualquier imagen soportada a WebP, para que todas las fotos
    se guarden en un unico formato (igual que el logo del proyecto).

    Ademas limita la resolucion al maximo de exhibicion (no agranda fotos mas
    chicas) y, si se pide, genera una miniatura aparte para listados/grillas.
    """
    archivo.seek(0)
    with Image.open(archivo) as imagen:
        tiene_transparencia = imagen.mode in ("RGBA", "LA") or (
            imagen.mode == "P" and "transparency" in imagen.info
        )
        imagen = imagen.convert("RGBA") if tiene_transparencia else imagen.convert("RGB")
        imagen.thumbnail(TAMANO_MAX_DISPLAY, Image.LANCZOS)

        buffer = io.BytesIO()
        imagen.save(buffer, format="WEBP", quality=CALIDAD_WEBP)

        miniatura_contenido = None
        if generar_miniatura:
            miniatura = imagen.copy()
            miniatura.thumbnail(TAMANO_MINIATURA, Image.LANCZOS)
            buffer_miniatura = io.BytesIO()
            miniatura.save(buffer_miniatura, format="WEBP", quality=CALIDAD_WEBP)
            miniatura_contenido = ContentFile(buffer_miniatura.getvalue())

    nombre_base = archivo.name.rsplit(".", 1)[0]
    principal = ContentFile(buffer.getvalue(), name=f"{nombre_base}.webp")
    if generar_miniatura:
        return principal, miniatura_contenido
    return principal
