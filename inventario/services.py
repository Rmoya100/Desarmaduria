"""Casos de uso del modulo Gastos que no encajan naturalmente en un modelo
o un formulario: aqui vive el procesamiento de la imagen del comprobante,
separado para que `models.py` y `forms.py` no mezclen esa logica."""

import io

from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

MAX_IMAGEN_BYTES = 5 * 1024 * 1024  # 5 MB
FORMATOS_IMAGEN_PERMITIDOS = {"JPEG", "PNG", "WEBP", "BMP", "GIF"}
CALIDAD_WEBP = 82


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


def convertir_a_webp(archivo):
    """Convierte cualquier imagen soportada a WebP, para que todos los
    comprobantes se guarden en un unico formato (igual que el logo del
    proyecto)."""
    archivo.seek(0)
    with Image.open(archivo) as imagen:
        tiene_transparencia = imagen.mode in ("RGBA", "LA") or (
            imagen.mode == "P" and "transparency" in imagen.info
        )
        imagen = imagen.convert("RGBA") if tiene_transparencia else imagen.convert("RGB")

        buffer = io.BytesIO()
        imagen.save(buffer, format="WEBP", quality=CALIDAD_WEBP)

    nombre_base = archivo.name.rsplit(".", 1)[0]
    return ContentFile(buffer.getvalue(), name=f"{nombre_base}.webp")
