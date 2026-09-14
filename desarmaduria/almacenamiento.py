"""Almacenamiento de archivos estaticos para el entorno de desarrollo.

En produccion cada estatico lleva un hash de su contenido en el nombre
(`base.7bfa99f3.css`, via CompressedManifestStaticFilesStorage), asi que al
cambiar el archivo cambia la URL y el navegador nunca puede servir una
version vieja desde su cache.

Ese mecanismo no sirve en desarrollo: el manifiesto que lo sustenta solo
existe despues de `collectstatic`. Aca se consigue el mismo efecto por otra
via, agregando la fecha de modificacion del archivo como parametro de
consulta.
"""

import os

from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import StaticFilesStorage


class StaticFilesVersionados(StaticFilesStorage):
    """Devuelve las URLs de los estaticos con `?v=<mtime>` al final.

    Al editar un archivo cambia su fecha de modificacion, por lo tanto
    cambia la URL, y el navegador la trata como un recurso que nunca ha
    visto: lo descarga en vez de reutilizar el de su cache.
    """

    def url(self, name):
        url = super().url(name)
        # `finders` resuelve la ruta real dentro de STATICFILES_DIRS. No se
        # usa self.path() porque en desarrollo apunta a STATIC_ROOT, que
        # contiene la copia de collectstatic y no el archivo que se edita.
        ruta = finders.find(name)
        if not ruta:
            return url
        try:
            marca = int(os.path.getmtime(ruta))
        except OSError:
            # Si el archivo no se puede leer, la URL sin version sigue
            # siendo valida: es preferible a romper el renderizado.
            return url
        separador = "&" if "?" in url else "?"
        return f"{url}{separador}v={marca}"
